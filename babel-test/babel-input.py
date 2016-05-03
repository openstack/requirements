#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


"""Test input for Babel"""


from oslo.i18n import _
from oslo.i18n import _LE
from oslo_log import log as logging

LOG = logging.getLogger(__name__)


def just_testing():
    """Just some random commands for Babel to extract strings from"""

    LOG.exception(_LE("LE translated string1"))
    LOG.exception(_LE("LE translated string2"))
    print(_("Normal translated string1"))
    # Translators: Comment for string2
    print(_("Normal translated string2"))
