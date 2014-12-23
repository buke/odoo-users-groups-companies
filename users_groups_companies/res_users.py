# -*- coding: utf-8 -*-
##############################################################################
#
#    User Role/Group Per Company
#    Copyright 2014 wangbuke <wangbuke@gmail.com>
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
import itertools
import logging
from functools import partial
from itertools import repeat

from lxml import etree
from lxml.builder import E

import openerp
from openerp import SUPERUSER_ID, models
from openerp import tools
import openerp.exceptions
from openerp.osv import fields, osv, expression
from openerp.tools.translate import _
from openerp.http import request

_logger = logging.getLogger(__name__)

class res_users_groups_companies(osv.osv):
    _name = "res.users.groups.companies"
    _description = "Access Groups"
    _table = "res_groups_users_rel"
    _log_access = True

    _columns = {
        'uid': fields.many2one('res.users', 'Users'),
        'gid': fields.many2one('res.groups', 'Groups'),
        'company_id': fields.many2one('res.company', 'Company', context={'user_preference': True}),
        'active': fields.boolean('Active'),
        'transfer': fields.boolean('Transfer', help='Can transfer to Other'),
    }

    _sql_constraints = [
        ('uid_gid_company_uniq', 'unique (uid,gid,company_id)', 'The User And Group must be unique per company !')
    ]

    def init(self, cr):
        cr.execute("ALTER TABLE res_groups_users_rel DROP CONSTRAINT IF EXISTS res_groups_users_rel_gid_uid_key")
        cr.commit()
        try:
            cr.execute("ALTER TABLE res_groups_users_rel ADD COLUMN id SERIAL")
            cr.execute("UPDATE res_groups_users_rel SET id = DEFAULT")
            cr.execute("ALTER TABLE res_groups_users_rel ADD PRIMARY KEY (id)")
        except:
            pass

    def _get_company(self, cr, uid, context=None, uid2=False):
        return self.pool.get('res.users')._get_company(cr, uid, context=context, uid2=uid2)

    _defaults = {
        'company_id': _get_company,
        'active': True,
        'transfer': False,
    }

    def create(self, cr, uid, data, context=None):
        self.pool.get('ir.rule').clear_cache(cr, uid)
        return super(res_users_groups_companies, self).create(cr, uid, data, context=context)

    def write(self, cr, uid, ids, values, context=None):
        self.pool.get('ir.rule').clear_cache(cr, uid)
        return super(res_users_groups_companies, self).write(cr, uid, ids, values, context=context)

    def unlink(self, cr, uid, ids, context=None):
        self.pool.get('ir.rule').clear_cache(cr, uid)
        return super(res_users_groups_companies, self).unlink(cr, uid, ids, context)



def name_boolean_group(id, company_id):
    return 'in_com_%s_group_%s' % (str(company_id), str(id))

def name_selection_groups(ids, company_id):
    return 'sel_com_%s_groups_%s' % (str(company_id), '_'.join(map(str, ids)))

def is_boolean_group(name):
    return name.startswith('in_com_')

def is_selection_groups(name):
    return name.startswith('sel_com_')

def is_reified_group(name):
    return is_boolean_group(name) or is_selection_groups(name)

def get_boolean_group(name):
    return int(name.split('_group_')[1])

def get_company(name):
    return int(name.split('_com_')[1].split('_')[0])

def get_selection_groups(name):
    return map(int, name.split('_groups_')[1].split('_'))

def partition(f, xs):
    "return a pair equivalent to (filter(f, xs), filter(lambda x: not f(x), xs))"
    yes, nos = [], []
    for x in xs:
        (yes if f(x) else nos).append(x)
    return yes, nos

def parse_m2m(commands):
    "return a list of ids corresponding to a many2many value"
    ids = []
    for command in commands:
        if isinstance(command, (tuple, list)):
            if command[0] in (1, 4):
                ids.append(command[2])
            elif command[0] == 5:
                ids = []
            elif command[0] == 6:
                ids = list(command[2])
        else:
            ids.append(command)
    return ids


class res_users(osv.osv):
    _inherit = 'res.users'

    def _create_ugc(self, cr, uid, user_id, group_id, company_id, context=None):
        group_ids = [g.id for g in self.pool.get('res.groups').browse(cr, SUPERUSER_ID, group_id, context=context).trans_implied_ids]
        for gid in group_ids:
            # self._create_ugc(cr, uid, user_id, gid, company_id, context=context)
            cr.execute('insert into res_groups_users_rel (uid,gid,company_id, active) values (%s,%s,%s,True)', (user_id, gid, company_id))
        cr.execute('insert into res_groups_users_rel (uid,gid,company_id, active) values (%s,%s,%s,True)', (user_id, group_id, company_id))

    def _unlink_ugc(self, cr, uid, user_id, group_id, company_id, context=None):
        group_ids = [g.id for g in self.pool.get('res.groups').browse(cr, SUPERUSER_ID, group_id, context=context).trans_implied_ids]
        for gid in group_ids:
            # self._unlink_ugc(cr, uid, user_id, gid, company_id, context=context)
            cr.execute('delete from res_groups_users_rel where uid=%s and gid=%s and company_id=%s', (user_id, gid, company_id))
        cr.execute('delete from res_groups_users_rel where uid=%s and gid=%s and company_id=%s', (user_id, group_id, company_id))


    def write(self, cr, uid, ids, values, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        res = super(res_users, self).write(cr, uid, ids, values, context)
        # self.pool['res.users'].has_company_group.clear_cache(self.pool['res.users'])
        # self.pool['res.users'].company_group_option.clear_cache(self.pool['res.users'])
        for user_id in ids:
            for key in values.iterkeys():
                if is_boolean_group(key):
                    value = values[key]
                    if value:
                        self._create_ugc(cr, uid, user_id, get_boolean_group(key), get_company(key), context=context)
                    else:
                        self._unlink_ugc(cr, uid, user_id, get_boolean_group(key), get_company(key), context=context)
                elif is_selection_groups(key):
                    value = values[key]
                    for group_id in get_selection_groups(key):
                        self._unlink_ugc(cr, uid, user_id, group_id, get_company(key), context=context)
                    if value:
                        self._create_ugc(cr, uid, user_id, value, get_company(key), context=context)
        return res


    def fields_get(self, cr, uid, allfields=None, context=None, write_access=True):
        res = super(res_users, self).fields_get(cr, uid, allfields, context, write_access)
        res.update(self._update_fields(cr, uid, context=context))
        return res

    def _update_fields(self, cr, uid, company_ids=None, context=None):
        if context is None:
            context = {}
        res = {}
        if company_ids is None:
            company_ids = self.pool.get('res.company').search(cr, uid, [])

        for company_id in company_ids:
            for app, kind, gs in self.pool['res.groups'].get_groups_by_application(cr, uid, context):
                if kind == 'selection':
                    # selection group field
                    tips = ['%s: %s' % (g.name, g.comment) for g in gs if g.comment]
                    res[name_selection_groups(map(int, gs), company_id)] = {
                        'type': 'selection',
                        'string': app and app.name or _('Other'),
                        'selection': [(False, '')] + [(g.id, g.name) for g in gs],
                        'help': '\n'.join(tips),
                        'exportable': False,
                        'selectable': False,
                    }
                else:
                    # boolean group fields
                    for g in gs:
                        res[name_boolean_group(g.id, company_id)] = {
                            'type': 'boolean',
                            'string': g.name,
                            'help': g.comment,
                            'exportable': False,
                            'selectable': False,
                        }
        return res


    def _add_new_groups(self, cr,  uid,  fields, values):
        """ add the given reified group fields into `values` """
        gids = set(parse_m2m(values.get('groups_id') or []))
        cids = set(parse_m2m(values.get('company_ids') or []))

        for f in fields:
            if is_boolean_group(f):
                if int(f.split('in_com_')[1].split('_')[0]) in cids:
                    values[f] = get_boolean_group(f) in gids
                else:
                    values[f] = False
            elif is_selection_groups(f):
                if int(f.split('sel_com_')[1].split('_')[0]) in cids:
                    selected = [gid for gid in get_selection_groups(f) if gid in gids]
                    values[f] = selected and selected[-1] or False
                else:
                    values[f] = False

    def default_get(self, cr, uid, fields, context=None):
        group_fields, fields = partition(is_reified_group, fields)
        fields1 = (fields + ['groups_id']) if group_fields else fields
        values = super(res_users, self).default_get(cr, uid, fields1, context)
        self._add_new_groups(cr, uid, group_fields, values)

        # add "default_groups_ref" inside the context to set default value for group_id with xml values
        if 'groups_id' in fields and isinstance(context.get("default_groups_ref"), list):
            groups = []
            ir_model_data = self.pool.get('ir.model.data')
            for group_xml_id in context["default_groups_ref"]:
                group_split = group_xml_id.split('.')
                if len(group_split) != 2:
                    raise osv.except_osv(_('Invalid context value'), _('Invalid context default_groups_ref value (model.name_id) : "%s"') % group_xml_id)
                try:
                    temp, group_id = ir_model_data.get_object_reference(cr, uid, group_split[0], group_split[1])
                except ValueError:
                    group_id = False
                groups += [group_id]
            values['groups_id'] = groups
        return values

    def _build_group_page(self, cr, uid, company_id, context=None):
        company = self.pool.get('res.company').browse(cr, uid, company_id, context=context)
        page = etree.Element('page', string=company.name)
        group_xml = etree.SubElement(page, 'group', col="4")

        xml1, xml2 = [], []
        xml1.append(E.separator(string=_('Application'), colspan="4"))
        for app, kind, gs in self.pool.get('res.groups').get_groups_by_application(cr, uid, context):
            attrs = {'groups': 'base.group_no_one'} if app and app.xml_id == 'base.module_category_hidden' else {}
            if kind == 'selection':
                # application name with a selection field
                field_name = name_selection_groups(map(int, gs), company_id)
                xml1.append(E.field(name=field_name, **attrs))
                xml1.append(E.newline())
            else:
                # application separator with boolean fields
                app_name = app and app.name or _('Other')
                xml2.append(E.separator(string=app_name, colspan="4", **attrs))
                for g in gs:
                    field_name = name_boolean_group(g.id, company_id)
                    xml2.append(E.field(name=field_name, **attrs))

        for xml in xml1:
            group_xml.append(xml)
        for xml in xml2:
            group_xml.append(xml)

        return page

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        result = super(res_users, self).fields_view_get(cr, uid, view_id, view_type, context=context, toolbar=toolbar, submenu=submenu)
        model, user_form_view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'view_users_form')
        company_ids = self.pool.get('res.company').search(cr, uid, [])

        if user_form_view_id == view_id:
            result['fields'].update(self.fields_get(cr, uid))
            eview = etree.fromstring(result['arch'])
            eviews = eview.xpath("//page")
            access_page = eview.xpath("//page")[0]
            for company_id in company_ids:
                # continue # 禁用
                company_group_page = self._build_group_page(cr, uid, company_id)
                access_page.addnext(company_group_page)
            access_page.getparent().remove(access_page)
            result['arch'] = etree.tostring(eview, pretty_print=True, encoding="utf-8")

        return result

    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        res = super(res_users, self).read(cr, uid, ids, fields, context=context, load=load)
        if 'groups_id' not in fields:
            return res
        group_fields = self._update_fields(cr, uid)
        for r in res:
            for k, v in group_fields.iteritems():
                if v['type'] == 'boolean':
                    r.update({k: self.has_company_group(cr, uid, r['id'], get_boolean_group(k), get_company(k))})
                elif v['type'] == 'selection':
                    r.update({k: self.company_group_option(cr, uid, r['id'], get_selection_groups(k), get_company(k))})
        return res

    # @tools.ormcache(skiparg=3)
    def has_company_group(self, cr, uid, user_id, group_id, company_id):
        cr.execute("SELECT 1 FROM res_groups_users_rel WHERE uid=%s AND gid=%s and company_id=%s and active = True", (user_id, group_id, company_id))
        return bool(cr.fetchone())

    # @tools.ormcache(skiparg=3)
    def company_group_option(self, cr, uid, user_id, group_ids, company_id):
        cr.execute("SELECT gid FROM res_groups_users_rel WHERE uid=%s AND gid in %s and company_id=%s and active = True", (user_id, tuple(group_ids), company_id))
        res = cr.fetchall()
        return res[-1] if res else False

    @tools.ormcache(skiparg=2)
    def has_group(self, cr, uid, group_ext_id):
        """Checks whether user belongs to given group.

        :param str group_ext_id: external ID (XML ID) of the group.
           Must be provided in fully-qualified form (``module.ext_id``), as there
           is no implicit module to use..
        :return: True if the current user is a member of the group with the
           given external ID (XML ID), else False.
        """
        assert group_ext_id and '.' in group_ext_id, "External ID must be fully qualified"
        module, ext_id = group_ext_id.split('.')
        cr.execute("""SELECT 1 FROM res_groups_users_rel WHERE active = True AND uid=%s AND gid IN
                        (SELECT res_id FROM ir_model_data WHERE module=%s AND name=%s)""",
                   (uid, module, ext_id))
        return bool(cr.fetchone())


class groups_view(osv.osv):
    _inherit = 'res.groups'

    def get_application_groups(self, cr, uid, domain=None, context=None):
        return self.search(cr, uid, domain or [])

    def get_groups_by_application(self, cr, uid, context=None):
        """ return all groups classified by application (module category), as a list of pairs:
                [(app, kind, [group, ...]), ...],
            where app and group are browse records, and kind is either 'boolean' or 'selection'.
            Applications are given in sequence order.  If kind is 'selection', the groups are
            given in reverse implication order.
        """
        def linearized(gs):
            gs = set(gs)
            # determine sequence order: a group should appear after its implied groups
            order = dict.fromkeys(gs, 0)
            for g in gs:
                for h in gs.intersection(g.trans_implied_ids):
                    order[h] -= 1
            # check whether order is total, i.e., sequence orders are distinct
            if len(set(order.itervalues())) == len(gs):
                return sorted(gs, key=lambda g: order[g])
            return None

        # classify all groups by application

        gids = self.get_application_groups(cr, uid, context=context)
        by_app, others = {}, []
        for g in self.browse(cr, uid, gids, context):
            if g.category_id:
                by_app.setdefault(g.category_id, []).append(g)
            else:
                others.append(g)
        # build the result
        res = []
        apps = sorted(by_app.iterkeys(), key=lambda a: a.sequence or 0)
        for app in apps:
            gs = linearized(by_app[app])
            if gs:
                res.append((app, 'selection', gs))
            else:
                res.append((app, 'boolean', by_app[app]))
        if others:
            res.append((False, 'boolean', others))
        return res


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
