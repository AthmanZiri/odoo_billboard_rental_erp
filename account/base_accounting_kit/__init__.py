# -*- # -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from . import models
from . import report
from . import wizard
from . import controllers


def pre_init_hook(env):
    """
    Drop the constraint 'followup_line_followup_id_fkey' before installing
    base_accounting_kit. This prevents the foreign key violation when
    Odoo tries to replace/delete account.followup records from a previously
    installed module (like om_accountant) with a restrict constraint.
    """
    try:
        env.cr.execute("ALTER TABLE followup_line DROP CONSTRAINT IF EXISTS followup_line_followup_id_fkey")
        env.cr.execute("DELETE FROM followup_line")
        env.cr.execute("DELETE FROM account_followup")
    except Exception as e:
        pass