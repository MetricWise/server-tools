# Copyright 2016 ForgeFlow S.L.
# Copyright 2016 Serpent Consulting Services Pvt. Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.osv import expression
from odoo.tests.common import TransactionCase


class QueryGenerationCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(QueryGenerationCase, cls).setUpClass()
        # Remove this variable in v16 and put instead:
        # from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT
        DISABLED_MAIL_CONTEXT = {
            "tracking_disable": True,
            "mail_create_nolog": True,
            "mail_create_nosubscribe": True,
            "mail_notrack": True,
            "no_reset_password": True,
        }
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))
        cls.ResPartner = cls.env["res.partner"]
        cls.TrgmIndex = cls.env["trgm.index"]
        cls.ResPartnerCategory = cls.env["res.partner.category"]

    def test_fuzzy_where_generation(self):
        """Check the generation of the where clause."""
        # the added fuzzy search operator should be available in the allowed
        # operators
        self.assertIn("%", expression.TERM_OPERATORS)

        # create new query with fuzzy search operator
        query = self.ResPartner._where_calc([("name", "%", "test")], active_test=False)
        from_clause, where_clause, where_clause_params = query.get_sql()

        # the % parameter has to be escaped (%%) for the string replation
        self.assertEqual(where_clause, """("res_partner"."name" %% %s)""")

        # test the right sql query statement creation
        # now there should be only one '%'
        complete_where = self.env.cr.mogrify(
            "SELECT FROM {} WHERE {}".format(from_clause, where_clause),
            where_clause_params,
        )
        self.assertEqual(
            complete_where,
            b'SELECT FROM "res_partner" WHERE ' b'("res_partner"."name" % \'test\')',
        )

    def test_fuzzy_where_generation_translatable(self):
        """Check the generation of the where clause for translatable fields."""
        # create new query with fuzzy search operator
        query = self.ResPartnerCategory.with_context(lang="de_DE")._where_calc(
            [("name", "%", "Goschaeftlic")], active_test=False
        )
        from_clause, where_clause, where_clause_params = query.get_sql()

        # the % parameter has to be escaped (%%) for the string replation
        self.assertIn(
            """COALESCE("res_partner_category__name"."value", "res_partner_category"."name") %% %s""",  # noqa
            where_clause,
        )

        complete_where = self.env.cr.mogrify(
            "SELECT FROM {} WHERE {}".format(from_clause, where_clause),
            where_clause_params,
        )

        self.assertIn(
            b"""SELECT FROM "res_partner_category" LEFT JOIN "ir_translation" AS "res_partner_category__name" ON ("res_partner_category"."id" = "res_partner_category__name"."res_id" AND "res_partner_category__name"."type" = \'model\' AND "res_partner_category__name"."name" = \'res.partner.category,name\' AND "res_partner_category__name"."lang" = \'de_DE\' AND "res_partner_category__name"."value" != \'\') WHERE COALESCE("res_partner_category__name"."value", "res_partner_category"."name") % \'Goschaeftlic\'""",  # noqa
            complete_where,
        )

    def test_fuzzy_search(self):
        """Test the fuzzy search itself."""
        if self.TrgmIndex._trgm_extension_exists() != "installed":
            return

        if not self.TrgmIndex.index_exists("res.partner", "name"):
            field_partner_name = self.env.ref("base.field_res_partner__name")
            self.TrgmIndex.create(
                {"field_id": field_partner_name.id, "index_type": "gin"}
            )

        partner1 = self.ResPartner.create({"name": "John Smith"})
        partner2 = self.ResPartner.create({"name": "John Smizz"})
        partner3 = self.ResPartner.create({"name": "Linus Torvalds"})

        res = self.ResPartner.search([("name", "%", "Jon Smith")])
        self.assertIn(partner1.id, res.ids)
        self.assertIn(partner2.id, res.ids)
        self.assertNotIn(partner3.id, res.ids)

        res = self.ResPartner.search([("name", "%", "Smith John")])
        self.assertIn(partner1.id, res.ids)
        self.assertIn(partner2.id, res.ids)
        self.assertNotIn(partner3.id, res.ids)
