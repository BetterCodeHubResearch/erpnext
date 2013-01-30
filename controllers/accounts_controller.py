# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes
from webnotes.utils import flt
from webnotes.model.doc import addchild
from utilities.transaction_base import TransactionBase

class AccountsController(TransactionBase):
	def get_gl_dict(self, args, cancel):
		"""this method populates the common properties of a gl entry record"""
		gl_dict = {
			'company': self.doc.company, 
			'posting_date': self.doc.posting_date,
			'voucher_type': self.doc.doctype,
			'voucher_no': self.doc.name,
			'aging_date': self.doc.fields.get("aging_date") or self.doc.posting_date,
			'remarks': self.doc.remarks,
			'is_cancelled': cancel and "Yes" or "No",
			'fiscal_year': self.doc.fiscal_year,
			'debit': 0,
			'credit': 0,
			'is_opening': self.doc.fields.get("is_opening") or "No",
		}
		gl_dict.update(args)
		return gl_dict
		
	def get_stock_in_hand_account(self):
		stock_in_hand = webnotes.conn.get_value("Company", self.doc.company, "stock_in_hand")	
		if not stock_in_hand:
			webnotes.msgprint("""Please specify "Stock In Hand" account 
				for company: %s""" % (self.doc.company,), raise_exception=1)
				
		return stock_in_hand
		
	def clear_unallocated_advances(self, parenttype, parentfield):
		for d in self.doclist:
			if d.parentfield == parentfield and flt(d.allocated_amount) == 0:
				self.doclist.remove(d)
			
		webnotes.conn.sql("""delete from `tab%s` where parent = %s 
			and ifnull(allocated_amount, 0) = 0""" % (parenttype, '%s'), self.doc.name)			
		
	def get_advances(self, account_head, parenttype, parentfield, dr_or_cr):
		res = webnotes.conn.sql("""select t1.name as jv_no, t1.remark, 
			t2.%s as amount, t2.name as jv_detail_no
			from `tabJournal Voucher` t1, `tabJournal Voucher Detail` t2 
			where t1.name = t2.parent and t2.account = %s and t2.is_advance = 'Yes' 
			and (t2.against_voucher is null or t2.against_voucher = '')
			and (t2.against_invoice is null or t2.against_invoice = '') 
			and (t2.against_jv is null or t2.against_jv = '') 
			and t1.docstatus = 1 order by t1.posting_date""" % 
			(dr_or_cr, '%s'), account_head, as_dict=1)
			
		self.doclist = self.doc.clear_table(self.doclist, parentfield)
		for d in res:
			add = addchild(self.doc, parentfield, parenttype, self.doclist)
			add.journal_voucher = d.jv_no
			add.jv_detail_no = d.jv_detail_no
			add.remarks = d.remark
			add.advance_amount = flt(d.amount)
			add.allocate_amount = 0