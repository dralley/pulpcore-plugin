#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

# Python
import mock
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil
import mock_plugins

from pulp.server.content.conduits.unit_import import ImportUnitConduit, ImportConduitException
from pulp.server.content.conduits._common import to_plugin_unit
import pulp.server.content.types.database as types_database
import pulp.server.content.types.model as types_model
from pulp.server.db.model.gc_repository import Repo, RepoContentUnit
import pulp.server.managers.repo.cud as repo_manager
import pulp.server.managers.repo.importer as importer_manager
import pulp.server.managers.repo.unit_association as association_manager
import pulp.server.managers.repo.unit_association_query as association_query_manager
import pulp.server.managers.content.cud as content_manager
import pulp.server.managers.content.query as content_query_manager

# constants --------------------------------------------------------------------

MOCK_TYPE_DEF = types_model.TypeDefinition('mock-type', 'Mock Type', 'Used by the mock importer', ['key-1'], [], [])


# -- test cases ---------------------------------------------------------------

class RepoSyncConduitTests(testutil.PulpTest):

    def clean(self):
        super(RepoSyncConduitTests, self).clean()
        types_database.clean()

        RepoContentUnit.get_collection().remove()
        Repo.get_collection().remove()

    def setUp(self):
        super(RepoSyncConduitTests, self).setUp()
        mock_plugins.install()
        types_database.update_database([MOCK_TYPE_DEF])

        self.repo_manager = repo_manager.RepoManager()
        self.importer_manager = importer_manager.RepoImporterManager()
        self.association_manager = association_manager.RepoUnitAssociationManager()
        self.association_query_manager = association_query_manager.RepoUnitAssociationQueryManager()
        self.content_manager = content_manager.ContentManager()
        self.content_query_manager = content_query_manager.ContentQueryManager()

        self.repo_manager.create_repo('source_repo')

        self.repo_manager.create_repo('dest_repo')
        self.importer_manager.set_importer('dest_repo', 'mock-importer', {})

        self.conduit = self._conduit('dest_repo')

    def test_str(self):
        """
        Makes sure the __str__ implementation does not raise an error.
        """
        str(self.conduit)

    def test_associate_unit(self):

        # Setup
        self.content_manager.add_content_unit('mock-type', 'unit_1', {'key-1' : 'unit-1'})
        self.association_manager.associate_unit_by_id('source_repo', 'mock-type', 'unit_1', association_manager.OWNER_TYPE_USER, 'admin')

        pulp_unit = self.association_query_manager.get_units('source_repo')[0]
        type_def = types_database.type_definition('mock-type')
        plugin_unit = to_plugin_unit(pulp_unit, type_def)

        # Test
        self.conduit.associate_unit(plugin_unit)

        # Verify
        associated_units = self.association_query_manager.get_units('dest_repo')
        self.assertEqual(1, len(associated_units))

    def test_associate_unit_server_error(self):
        """
        Makes sure the conduit wraps any exception emerging from the server.
        """

        # Setup
        mock_association_manager = mock.Mock()
        mock_association_manager.associate_unit_by_id.side_effect = Exception()

        conduit = ImportUnitConduit('dest_repo', 'test-importer', mock_association_manager, self.importer_manager)

        # Test
        try:
           conduit.associate_unit(None)
           self.fail('Exception expected')
        except ImportConduitException:
            pass

    # -- utilities ------------------------------------------------------------

    def _conduit(self, repo_id):
        """
        Convenience method for creating a conduit.
        """
        conduit = ImportUnitConduit(repo_id, 'test-importer', self.association_manager, self.importer_manager)
        return conduit