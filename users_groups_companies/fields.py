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

import openerp

def get_company(cr, uid):
    cr.execute("SELECT company_id FROM res_users WHERE id=%s", (uid,))
    company_id = cr.fetchone()
    company_id = company_id[0] if company_id else False
    return company_id

def set(self, cr, model, id, name, values, user=None, context=None):
    if not context:
        context = {}
    if not values:
        return

    rel, id1, id2 = self._sql_names(model)
    obj = model.pool[self._obj]
    for act in values:
        if not (isinstance(act, list) or isinstance(act, tuple)) or not act:
            continue
        if act[0] == 0:
            idnew = obj.create(cr, user, act[2], context=context)
            company_id = get_company(cr, idnew) if rel == 'res_groups_users_rel' else False
            if rel == 'res_groups_users_rel' and company_id:
                cr.execute('insert into '+rel+' ('+id1+','+id2+', company_id) values (%s,%s,%s)', (id, idnew, company_id))
            else:
                cr.execute('insert into '+rel+' ('+id1+','+id2+') values (%s,%s)', (id, idnew))
        elif act[0] == 1:
            obj.write(cr, user, [act[1]], act[2], context=context)
        elif act[0] == 2:
            obj.unlink(cr, user, [act[1]], context=context)
        elif act[0] == 3:
            company_id = get_company(cr, id) if rel == 'res_groups_users_rel' and id1 == 'uid' else False
            company_id = get_company(cr, act[1]) if rel == 'res_groups_users_rel' and id1 == 'gid' else company_id or False
            if rel == 'res_groups_users_rel' and company_id:
                cr.execute('delete from '+rel+' where ' + id1 + '=%s and '+ id2 + '=%s and company_id=%s', (id, act[1], company_id))
            else:
                cr.execute('delete from '+rel+' where ' + id1 + '=%s and '+ id2 + '=%s', (id, act[1]))
        elif act[0] == 4:
            # following queries are in the same transaction - so should be relatively safe
            company_id = get_company(cr, id) if rel == 'res_groups_users_rel' and id1 == 'uid' else False
            company_id = get_company(cr, act[1]) if rel == 'res_groups_users_rel' and id1 == 'gid' else company_id or False
            if rel == 'res_groups_users_rel' and company_id:
                cr.execute('SELECT 1 FROM '+rel+' WHERE '+id1+' = %s and '+id2+' = %s and company_id=%s', (id, act[1], company_id))
                if not cr.fetchone():
                    cr.execute('insert into '+rel+' ('+id1+','+id2+', company_id) values (%s,%s,%s)', (id, act[1], company_id))
            else:
                cr.execute('SELECT 1 FROM '+rel+' WHERE '+id1+' = %s and '+id2+' = %s', (id, act[1]))
                if not cr.fetchone():
                    cr.execute('insert into '+rel+' ('+id1+','+id2+') values (%s,%s)', (id, act[1]))
        elif act[0] == 5:
            company_id = get_company(cr, id) if rel == 'res_groups_users_rel' and id1 == 'uid' else False
            company_id = get_company(cr, act[1]) if rel == 'res_groups_users_rel' and id1 == 'gid' else company_id or False
            if rel == 'res_groups_users_rel' and company_id:
                cr.execute('delete from '+rel+' where ' + id1 + ' = %s and company_id=%s', (id, company_id))
            else:
                cr.execute('delete from '+rel+' where ' + id1 + ' = %s', (id,))
        elif act[0] == 6:
            d1, d2,tables = obj.pool.get('ir.rule').domain_get(cr, user, obj._name, context=context)
            if d1:
                d1 = ' and ' + ' and '.join(d1)
            else:
                d1 = ''
            cr.execute('delete from '+rel+' where '+id1+'=%s AND '+id2+' IN (SELECT '+rel+'.'+id2+' FROM '+rel+', '+','.join(tables)+' WHERE '+rel+'.'+id1+'=%s AND '+rel+'.'+id2+' = '+obj._table+'.id '+ d1 +')', [id, id]+d2)

            for act_nbr in act[2]:
                company_id = get_company(cr, id) if rel == 'res_groups_users_rel' and id1 == 'uid' else False
                company_id = get_company(cr, act_nbr) if rel == 'res_groups_users_rel' and id1 == 'gid' else company_id or False
                if rel == 'res_groups_users_rel' and company_id:
                    cr.execute('insert into '+rel+' ('+id1+','+id2+', company_id) values (%s, %s, %s)', (id, act_nbr, company_id))
                else:
                    cr.execute('insert into '+rel+' ('+id1+','+id2+') values (%s, %s)', (id, act_nbr))


openerp.osv.fields.many2many.set = set

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
