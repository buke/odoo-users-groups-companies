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
{
    'name': 'User Role/Group Per Company',
    'version': '0.1',
    'category': 'Tools',
    'summary': '每个公司都可以独立设置用户权限',
    'description': """
每个公司都可以独立设置用户权限
""",
    'author': 'wangbuke@gmail.com',
    'website': 'http://buke.github.io',
    'depends': ['base'],
    'data': [
        'res_users_view.xml',
    ],
    'js': [
    ],
    'css': [
    ],
    'qweb' : [
    ],
    'installable': True,
    'images': [],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

