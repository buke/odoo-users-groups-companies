# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import time

from openerp import SUPERUSER_ID
from openerp import tools
from openerp.osv import fields, osv, expression
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.misc import unquote as unquote

class ir_rule(osv.osv):
    _inherit = 'ir.rule'
    _order = 'name'
    _MODES = ['read', 'write', 'create', 'unlink']

    @tools.ormcache(skiparg=2)
    def _compute_domain2(self, cr, uid, model_name, mode="read"):
        if mode not in self._MODES:
            raise ValueError('Invalid mode: %r' % (mode,))

        if uid == SUPERUSER_ID:
            return None
        cr.execute("""SELECT r.id
                FROM ir_rule r
                JOIN ir_model m ON (r.model_id = m.id)
                WHERE m.model = %s
                AND r.active is True
                AND r.perm_""" + mode + """
                AND (r.id IN (SELECT rule_group_id FROM rule_group_rel g_rel
                            JOIN res_groups_users_rel u_rel ON (g_rel.group_id = u_rel.gid)
                            WHERE u_rel.uid = %s) OR r.global)""", (model_name, uid))
        rule_ids = [x[0] for x in cr.fetchall()]
        if rule_ids:
            # browse user as super-admin root to avoid access errors!
            user = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid)
            global_domains = []                 # list of domains
            group_domains = {}                  # map: group -> list of domains
            for rule in self.browse(cr, SUPERUSER_ID, rule_ids):
                # read 'domain' as UID to have the correct eval context for the rule.
                rule_domain = self.read(cr, uid, [rule.id], ['domain'])[0]['domain']
                dom = expression.normalize_domain(rule_domain)
                for group in rule.groups:
                    if group in user.groups_id:
                        group_domains.setdefault(group, []).append(dom)
                if not rule.groups:
                    global_domains.append(dom)
            # combine global domains and group domains
            if group_domains:
                group_domain = expression.OR(map(expression.OR, group_domains.values()))
            else:
                group_domain = []
            domain = expression.AND(global_domains + [group_domain])

            if 'company_id' in self.pool.get(model_name):
                cr.execute("""SELECT r.group_id
                        FROM ir_model_access r
                        JOIN ir_model m ON (r.model_id = m.id)
                        WHERE m.model = %s
                        AND r.active is True
                        AND r.perm_""" + mode + """
                        """, (model_name, ))
                group_ids = [x[0] for x in cr.fetchall() if x[0]]

                cr.execute("""SELECT company_id
                        FROM res_groups_users_rel
                        WHERE uid = %s and gid in %s
                        """, (uid, tuple(group_ids)))
                company_ids = [x[0] for x in cr.fetchall() if x[0]]
                company_domain = [('company_id', 'child_of', company_ids)]
                domain = expression.OR([domain] + [company_domain])
            return domain
        return []

    def domain_get(self, cr, uid, model_name, mode='read', context=None):
        dom = self._compute_domain2(cr, uid, model_name, mode)
        if dom:
            # _where_calc is called as superuser. This means that rules can
            # involve objects on which the real uid has no acces rights.
            # This means also there is no implicit restriction (e.g. an object
            # references another object the user can't see).
            query = self.pool[model_name]._where_calc(cr, SUPERUSER_ID, dom, active_test=False)
            return query.where_clause, query.where_clause_params, query.tables
        return [], [], ['"' + self.pool[model_name]._table + '"']

    def clear_cache(self, cr, uid):
        super(ir_rule, self).clear_cache(cr, uid)
        # self._compute_domain2.clear_cache(self)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
