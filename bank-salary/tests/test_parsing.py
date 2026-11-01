import unittest

from bank_salary.parsing import extract_salary, text_from_html


class SalaryParsingTests(unittest.TestCase):
    def test_ms_annual(self):
        text = "Expected base pay rates for the role will be between $150,000 and $225,000 per year at the commencement of employment."
        rows = extract_salary("MS", text, [])
        self.assertEqual(len(rows), 1)
        self.assertEqual(
            (rows[0]["minimum"], rows[0]["maximum"], rows[0]["period"]), (150000, 225000, "year")
        )
        self.assertIn("$150,000", rows[0]["evidence"])

    def test_gs_region_and_unknown_period(self):
        text = "The expected base salary for this New York, NY, United States-based position is $115000-$180000. In addition, you may be eligible for a discretionary bonus."
        row = extract_salary("GS", text, [])[0]
        self.assertEqual((row["minimum"], row["maximum"]), (115000, 180000))
        self.assertEqual(row["period"], "unspecified")
        self.assertIn("New York", row["region"])
        self.assertEqual(row["pay_type"], "base")

    def test_jpm_keeps_regions_separate_and_unit_unknown(self):
        fields = [
            {
                "Prompt": "Base Pay/Salary",
                "Value": "New York,NY $205,000.00-$285,000.00; Chicago,IL $190,000.00-$260,000.00",
            }
        ]
        rows = extract_salary("JPM", "", fields)
        self.assertEqual(len(rows), 2)
        self.assertEqual([r["region"] for r in rows], ["New York,NY", "Chicago,IL"])
        self.assertEqual([r["minimum"] for r in rows], [205000, 190000])
        self.assertEqual(rows[0]["period"], "unspecified")

    def test_small_amount_is_not_automatically_hourly(self):
        row = extract_salary(
            "JPM", "", [{"Prompt": "Base Pay/Salary", "Value": "Brooklyn,NY $25.00-$30.48"}]
        )[0]
        self.assertEqual(row["period"], "unspecified")
        self.assertEqual(row["minimum"], 25)

    def test_explicit_hourly_and_fixed_pay(self):
        rows = extract_salary(
            "MS", "Expected base pay rates will be between $25.00 and $30.48 per hour.", []
        )
        self.assertEqual(rows[0]["period"], "hour")
        fixed = extract_salary(
            "JPM",
            "",
            [{"Prompt": "Base Pay/Salary", "Value": "New York,NY $110,000.00-$110,000.00"}],
        )[0]
        self.assertEqual((fixed["minimum"], fixed["maximum"]), (110000, 110000))

    def test_ignores_assets_and_bonus_amounts(self):
        text = "We supervise over $1.8 trillion in assets. A discretionary bonus of $10,000 may be offered."
        self.assertEqual(extract_salary("GS", text, []), [])

    def test_keeps_multiple_base_salary_statements(self):
        text = "The expected base salary for this New York-based position is $100,000-$150,000 per year. The expected base salary for this California-based position is $110,000-$160,000 per year."
        rows = extract_salary("GS", text, [])
        self.assertEqual(len(rows), 2)
        self.assertEqual([r["minimum"] for r in rows], [100000, 110000])
        self.assertNotEqual(rows[0]["region"], rows[1]["region"])

    def test_inverted_range_is_reviewable(self):
        row = extract_salary(
            "JPM", "", [{"Prompt": "Base Pay/Salary", "Value": "NY $200,000-$100,000"}]
        )[0]
        self.assertEqual(row["parse_status"], "review")

    def test_html_decoding(self):
        self.assertEqual(
            text_from_html("<p>Base&nbsp;pay</p><p>$10 &amp; $20</p>"), "Base pay $10 & $20"
        )

    def test_fixed_single_salary_in_description_and_field(self):
        text = "The expected base salary for this New York-based position is $110,000 per year."
        row = extract_salary("GS", text, [])[0]
        self.assertEqual((row["minimum"], row["maximum"], row["period"]), (110000, 110000, "year"))
        row = extract_salary(
            "JPM", "", [{"Prompt": "Base Pay/Salary", "Value": "New York,NY $110000"}]
        )[0]
        self.assertEqual((row["minimum"], row["maximum"]), (110000, 110000))

    def test_range_after_bonus_or_assets_clause_is_not_base_pay(self):
        for ending in (
            "with a discretionary bonus of $10,000-$20,000",
            "for advisers managing $1,000,000-$2,000,000 in assets",
        ):
            rows = extract_salary("GS", "Expected base salary is $100,000-$150,000 " + ending, [])
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["minimum"], 100000)

    def test_bonus_annual_does_not_define_base_salary_period(self):
        rows = extract_salary(
            "GS",
            "Expected base salary is $100,000-$150,000 and employees may be eligible for an annual discretionary bonus.",
            [],
        )
        self.assertEqual(rows[0]["period"], "unspecified")

    def test_null_salary_field_is_missing(self):
        self.assertEqual(
            extract_salary("JPM", "", [{"Prompt": "Base Pay/Salary", "Value": None}]), []
        )

    def test_ms_salary_without_dollar_sign_and_k_shorthand(self):
        text = "Expected base pay rates for the role will be between 95000 and 155000 per year at the commencement of employment."
        row = extract_salary("MS", text, [])[0]
        self.assertEqual((row["minimum"], row["maximum"], row["period"]), (95000, 155000, "year"))
        row = extract_salary(
            "MS", "Expected base pay rates will be between $105K-$140K per year.", []
        )[0]
        self.assertEqual((row["minimum"], row["maximum"]), (105000, 140000))

    def test_source_typo_is_review_instead_of_false_fixed_amount(self):
        row = extract_salary(
            "MS", "Expected base pay rates will be between $108,000 and per$154,500 year.", []
        )[0]
        self.assertEqual(
            (row["minimum"], row["maximum"], row["parse_status"]), (108000, 154500, "review")
        )

    def test_multiple_fixed_grade_amounts_remain_separate(self):
        rows = extract_salary(
            "MS",
            "Expected base pay rates for the role will be $225,000 per year for Vice President, and $300,000 per year for Executive Director, at the commencement of employment.",
            [],
        )
        self.assertEqual(
            [(r["minimum"], r["maximum"]) for r in rows], [(225000, 225000), (300000, 300000)]
        )
        self.assertIn("Executive Director", rows[1]["evidence"])

    def test_gs_campus_paired_salary_fields(self):
        fields = [
            {"Prompt": "Anaplan Salary Range Lower Limit\t", "Value": "65,000"},
            {"Prompt": "Anaplan Salary Range Upper Limit\t", "Value": "95,000"},
        ]
        row = extract_salary("GS", "", fields)[0]
        self.assertEqual(
            (row["minimum"], row["maximum"], row["period"], row["pay_type"]),
            (65000, 95000, "unspecified", "salary_unspecified"),
        )
        self.assertEqual(extract_salary("GS", "", fields[:1]), [])

    def test_malformed_thousands_separator_is_retained_as_review(self):
        row = extract_salary(
            "GS",
            "The expected base salary for this New York-based position is $115,000-$30,0000.",
            [],
        )[0]
        self.assertEqual(
            (row["minimum"], row["maximum"], row["parse_status"]), (115000, 300000, "review")
        )

    def test_structured_locations_can_be_newline_or_space_separated(self):
        for separator in ("\n", " "):
            value = (
                "New York, NY $114,000.00-$150,000.00"
                + separator
                + "Jersey City, NJ $114,000.00-$150,000.00"
            )
            rows = extract_salary("JPM", "", [{"Prompt": "Base Pay/Salary", "Value": value}])
            self.assertEqual(len(rows), 2)
            self.assertEqual([r["region"] for r in rows], ["New York, NY", "Jersey City, NJ"])
            self.assertEqual([r["minimum"] for r in rows], [114000, 114000])

    def test_bofa_pay_range_keeps_its_pay_transparency_locations(self):
        text = (
            "Hours Per Week: 40 Pay Transparency details US - MA - Boston - 100 Federal St - 100 Federal St Lp (MA5100), "
            "US - NY - New York - ONE BRYANT PARK - BANK OF AMERICA TOWER (NY1100) Pay and benefits information "
            "Pay range $130,000.00 - $201,200.00 annualized salary, offers to be determined based on experience, "
            "education and skill set. Discretionary incentive eligible This role is eligible to participate in the "
            "annual discretionary plan. Pay Transparency details US - CA - San Francisco - 555 California St (CA5550) "
            "Pay and benefits information Pay range $25.97 - $31.75 hourly pay, offers to be determined."
        )
        rows = extract_salary("BOFA", text, [])
        self.assertEqual(
            [(r["minimum"], r["maximum"], r["period"]) for r in rows],
            [(130000, 201200, "year"), (25.97, 31.75, "hour")],
        )
        self.assertTrue(rows[0]["region"].startswith("US - MA - Boston"))
        self.assertIn("US - NY - New York", rows[0]["region"])
        self.assertEqual(rows[1]["region"], "US - CA - San Francisco - 555 California St (CA5550)")
        self.assertEqual({r["pay_type"] for r in rows}, {"base"})
        self.assertIn("Pay range $130,000.00 - $201,200.00 annualized salary", rows[0]["evidence"])

    def test_citi_salary_range_applies_to_the_primary_location(self):
        text = (
            "Job Family: Private Banker Support ------------------------------------------------------ "
            "Primary Location: Jersey City New Jersey United States ------------------------------------------------------ "
            "Primary Location Full Time Salary Range: $98,960.00 - $148,440.00 In addition to salary, Citi's offerings "
            "may also include, for eligible employees, discretionary and formulaic incentive and retention awards."
        )
        rows = extract_salary("CITI", text, [])
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["minimum"], rows[0]["maximum"]), (98960, 148440))
        self.assertEqual(rows[0]["period"], "unspecified")
        self.assertEqual(rows[0]["region"], "Jersey City New Jersey United States")
        self.assertEqual(rows[0]["parse_status"], "parsed")


if __name__ == "__main__":
    unittest.main()
