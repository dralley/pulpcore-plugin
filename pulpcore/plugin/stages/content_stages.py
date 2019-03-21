from collections import defaultdict

from django.db import IntegrityError, transaction
from django.db.models import Q

from pulpcore.plugin.models import ContentArtifact

from .api import Stage


class QueryExistingContents(Stage):
    """
    A Stages API stage that saves :attr:`DeclarativeContent.content` objects and saves its related
    :class:`~pulpcore.plugin.models.ContentArtifact` objects too.

    This stage expects :class:`~pulpcore.plugin.stages.DeclarativeContent` units from `self._in_q`
    and inspects their associated :class:`~pulpcore.plugin.stages.DeclarativeArtifact` objects. Each
    :class:`~pulpcore.plugin.stages.DeclarativeArtifact` object stores one
    :class:`~pulpcore.plugin.models.Artifact`.

    This stage inspects any "unsaved" Content unit objects and searches for existing saved Content
    units inside Pulp with the same unit key. Any existing Content objects found, replace their
    "unsaved" counterpart in the :class:`~pulpcore.plugin.stages.DeclarativeContent` object.

    Each :class:`~pulpcore.plugin.stages.DeclarativeContent` is sent to `self._out_q` after it has
    been handled.

    This stage drains all available items from `self._in_q` and batches everything into one large
    call to the db for efficiency.
    """

    async def run(self):
        """
        The coroutine for this stage.

        Returns:
            The coroutine for this stage.
        """
        async for batch in self.batches():
            content_q_by_type = defaultdict(lambda: Q(_created=None))
            for d_content in batch:
                model_type = type(d_content.content)
                unit_q = d_content.content.q()
                content_q_by_type[model_type] = content_q_by_type[model_type] | unit_q

            for model_type in content_q_by_type.keys():
                for result in model_type.objects.filter(content_q_by_type[model_type]):
                    for d_content in batch:
                        if type(d_content.content) is not model_type:
                            continue
                        not_same_unit = False
                        for field in result.natural_key_fields():
                            in_memory_digest_value = getattr(d_content.content, field)
                            if in_memory_digest_value != getattr(result, field):
                                not_same_unit = True
                                break
                        if not_same_unit:
                            continue
                        d_content.content = result
            for d_content in batch:
                await self.put(d_content)


class ContentSaver(Stage):
    """
    A Stages API stage that saves :attr:`DeclarativeContent.content` objects and saves its related
    :class:`~pulpcore.plugin.models.ContentArtifact` objects too.

    This stage expects :class:`~pulpcore.plugin.stages.DeclarativeContent` units from `self._in_q`
    and inspects their associated :class:`~pulpcore.plugin.stages.DeclarativeArtifact` objects. Each
    :class:`~pulpcore.plugin.stages.DeclarativeArtifact` object stores one
    :class:`~pulpcore.plugin.models.Artifact`.

    Each "unsaved" Content objects is saved and a :class:`~pulpcore.plugin.models.ContentArtifact`
    objects too.

    Each :class:`~pulpcore.plugin.stages.DeclarativeContent` is sent to after it has been handled.

    This stage drains all available items from `self._in_q` and batches everything into one large
    call to the db for efficiency.
    """

    async def run(self):
        """
        The coroutine for this stage.

        Returns:
            The coroutine for this stage.
        """
        async for batch in self.batches():
            content_artifact_bulk = []
            new_batch = []
            with transaction.atomic():
                await self._pre_save(batch)
                content_to_save = defaultdict(list)

                for d_content in batch:
                    content_to_save[d_content.content.__class__].append(d_content.content)

                for ctype, typed_content in content_to_save.items():
                    saved_content = ctype.objects.bulk_get_or_create(typed_content)

                    for d_content, content in zip(batch, saved_content):
                        d_content.content = content
                        for d_artifact in d_content.d_artifacts:
                            artifact_already_saved = not d_artifact.artifact._state.adding

                            if artifact_already_saved:
                                artifact = d_artifact.artifact
                            else:
                                # set to None for lazy synced artifacts
                                artifact = None
                            content_artifact = ContentArtifact(
                                content=d_content.content,
                                artifact=artifact,
                                relative_path=d_artifact.relative_path
                            )
                            content_artifact_bulk.append(content_artifact)
                        new_batch.append(d_content)
                ContentArtifact.objects.bulk_get_or_create(content_artifact_bulk)
                await self._post_save(new_batch)
            for declarative_content in new_batch:
                await self.put(declarative_content)

    async def _pre_save(self, batch):
        """
        A hook plugin-writers can override to save related objects prior to content unit saving.

        This is run within the same transaction as the content unit saving.

        Args:
            batch (list of :class:`~pulpcore.plugin.stages.DeclarativeContent`): The batch of
                :class:`~pulpcore.plugin.stages.DeclarativeContent` objects to be saved.

        """
        pass

    async def _post_save(self, batch):
        """
        A hook plugin-writers can override to save related objects after content unit saving.

        This is run within the same transaction as the content unit saving.

        Args:
            batch (list of :class:`~pulpcore.plugin.stages.DeclarativeContent`): The batch of
                :class:`~pulpcore.plugin.stages.DeclarativeContent` objects to be saved.

        """
        pass


class ResolveContentFutures(Stage):
    """
    This stage resolves the futures in :class:`~pulpcore.plugin.stages.DeclarativeContent`.

    Futures results are set to the found/created :class:`~pulpcore.plugin.models.Content`.

    This is useful when data downloaded from the plugin API needs to be parsed by FirstStage to
    create additional :class:`~pulpcore.plugin.stages.DeclarativeContent` objects to be send down
    the pipeline. Consider an example where content type `Foo` references additional instances of a
    different content type `Bar`. Consider this code in FirstStage::

        # Create d_content and d_artifact for a `foo_a`
        foo_a = DeclarativeContent(..., does_batch=False)
        foo_a_future = foo_a.get_or_create_future()  # This is awaitable

        ...

        foo_a_content = await foo_a_future  # awaits until the foo_a reaches this stage

    This creates a "looping" pattern, of sorts, where downloaded content at the end of the pipeline
    can introduce new additional to-be-downloaded content at the beginning of the pipeline.
    """

    async def run(self):
        """
        The coroutine for this stage.

        Returns:
            The coroutine for this stage.
        """
        async for d_content in self.items():
            if d_content.future is not None:
                d_content.future.set_result(d_content.content)
            await self.put(d_content)
