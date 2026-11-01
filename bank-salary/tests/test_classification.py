import unittest

from bank_salary.classification import classify_job


def labels(title, **extra):
    result = classify_job({"title": title, **extra})
    return tuple(result[key]["label"] for key in ("department", "subdepartment", "occupation"))


class ClassificationTests(unittest.TestCase):
    def test_xva_trading_is_a_trader_but_explicit_support_roles_take_precedence(self):
        self.assertEqual(
            labels("xVA Trading - Fixed Income Division - Associate or Vice President"),
            ("マーケッツ", "債券部", "トレーダー"),
        )
        for title, role in [
            ("XVA Trading - Software Engineer", "エンジニア・開発"),
            ("XVA Trading Operations - Associate", "オペレーション"),
            ("XVA Trading - Business Management - Vice President", "経営企画・管理"),
            ("Market Risk - XVA (Risk Management) : Job Level - Associate", "リスク管理"),
        ]:
            with self.subTest(title=title):
                self.assertEqual(classify_job({"title": title})["occupation"]["label"], role)

    def test_investment_banking_and_markets_are_separate(self):
        cases = [
            (
                "Investment Banking M&A Associate – New York",
                ("投資銀行", "M&A", "投資銀行バンカー"),
            ),
            (
                "Fixed Income Institutional Sales - Vice President",
                ("マーケッツ", "債券部", "営業・セールス"),
            ),
            ("Equity Derivatives Trader - Associate", ("マーケッツ", "株式部", "トレーダー")),
            ("FX Options Sales Trader", ("マーケッツ", "為替部", "セールストレーダー")),
            (
                "GBM - Quantitative Rates Trading Strat, VP - New York",
                ("マーケッツ", "債券部", "クオンツ・ストラテジスト"),
            ),
        ]
        for title, expected in cases:
            with self.subTest(title=title):
                self.assertEqual(labels(title), expected)

    def test_business_and_occupation_do_not_overwrite_each_other(self):
        self.assertEqual(
            labels("Equity Trading Software Engineer"),
            ("Technology", "株式・デリバティブ技術", "エンジニア・開発"),
        )
        self.assertEqual(
            labels("Asset Management - Fixed Income Portfolio Manager"),
            ("資産運用", "債券運用", "運用・ポートフォリオ管理"),
        )
        self.assertEqual(
            labels("Relationship Executive - Innovation Economy Technology - Managing Director"),
            ("法人銀行", "イノベーション企業", "営業・セールス"),
        )
        self.assertEqual(
            labels("Fixed Income Division – Associate, Public Finance Investment Banking"),
            ("投資銀行", "公共・インフラ金融", "投資銀行バンカー"),
        )

    def test_functional_teams_are_not_forced_into_their_supported_product(self):
        self.assertEqual(
            labels("Legal, Equities Derivatives Attorney, Vice President"),
            ("コーポレート・共通部門", "法務", "法務"),
        )
        self.assertEqual(
            labels(
                "Valuation Controller - Vice President – Rates",
                department="Corporate Sector",
                job_level="Controller",
            ),
            ("コーポレート・共通部門", "財務・経理・税務", "財務・経理・税務"),
        )

    def test_combined_divisions_and_multi_product_roles_remain_explicit(self):
        result = classify_job(
            {"title": "Software Engineer, Global Banking & Markets, Front Office Technology"}
        )
        self.assertEqual(result["department"]["label"], "Technology")
        self.assertEqual(result["subdepartment"]["label"], "フロントオフィス技術")
        result = classify_job(
            {"title": "FICC and Equities (Sales and Trading) Quantitative Strats"}
        )
        self.assertEqual(result["subdepartment"]["label"], "商品横断（FICC・株式）")
        self.assertEqual(result["occupation"]["label"], "クオンツ・ストラテジスト")

    def test_body_fallback_uses_explicit_role_context_not_firm_boilerplate(self):
        generic = "Morgan Stanley provides investment banking, securities, investment management and wealth management services."
        self.assertEqual(labels("Associate", description=generic), ("未分類", "未分類", "未分類"))
        result = classify_job(
            {
                "title": "Associate",
                "description": generic
                + " As an Equity Derivatives Trader within our Global Markets team, you will price options.",
            }
        )
        self.assertEqual(result["department"]["label"], "マーケッツ")
        self.assertEqual(result["subdepartment"]["label"], "株式部")
        self.assertEqual(result["occupation"]["label"], "トレーダー")
        self.assertEqual(result["department"]["basis"], "本文の職務記述")
        self.assertIn("Equity Derivatives Trader", result["occupation"]["evidence"])

    def test_public_metadata_is_retained_as_evidence_and_missing_is_not_guessed(self):
        result = classify_job({"title": "Associate", "department": "Asset & Wealth Management"})
        self.assertEqual(result["department"]["label"], "資産運用・WM（横断）")
        self.assertEqual(result["department"]["basis"], "公開部門")
        self.assertEqual(result["occupation"]["label"], "未分類")
        self.assertEqual(
            labels(None, description=None, department=None), ("未分類", "未分類", "未分類")
        )

    def test_public_cib_is_broad_but_explicit_payments_title_refines_it(self):
        result = classify_job({"title": "Associate", "department": "Commercial & Investment Bank"})
        self.assertEqual(result["department"]["label"], "投資銀行・マーケッツ（横断）")
        result = classify_job(
            {
                "title": "Payments Sales Manager - Broker Dealers and Market Structure",
                "department": "Commercial & Investment Bank",
            }
        )
        self.assertEqual(result["department"]["label"], "決済・トランザクションバンキング")
        self.assertEqual(result["occupation"]["label"], "営業・セールス")

    def test_body_mentions_of_clients_and_partner_teams_do_not_become_the_role(self):
        cases = [
            (
                "Asset & Wealth Management, Private Wealth Management, Financial Investment Professional",
                "Act as a key liaison for client accounts to internal PWM stakeholders, including Operations and Compliance.",
            ),
            (
                "Global Banking & Markets Private, Transportation Finance, Vice President",
                "Serve as a hub of expertise, coordinating with Credit Risk, Legal, Compliance, and Operations to deliver the full capabilities.",
            ),
            (
                "Asset & Wealth Management, Employee Funds Analyst",
                "As the primary investment area within Goldman Sachs, we provide investment services for financial advisors and individuals.",
            ),
        ]
        for title, description in cases:
            with self.subTest(title=title):
                self.assertEqual(
                    classify_job({"title": title, "description": description})["occupation"][
                        "label"
                    ],
                    "未分類",
                )

    def test_private_equity_and_private_bank_unit_names_are_not_job_functions(self):
        result = classify_job(
            {"title": "Global Banking & Markets – Private Equity Capital Call Financing, Analyst"}
        )
        self.assertEqual(result["department"]["label"], "投資銀行・マーケッツ（横断）")
        result = classify_job({"title": "Private Bank - Associate"})
        self.assertEqual(result["occupation"]["label"], "未分類")

    def test_research_sector_names_do_not_replace_the_business_or_occupation(self):
        self.assertEqual(
            labels("US Equity Research - Large Cap Software - Associate"),
            ("リサーチ", "株式リサーチ", "リサーチ"),
        )
        self.assertEqual(
            labels("Equity Research – Associate, Fintech & Payments"),
            ("リサーチ", "株式リサーチ", "リサーチ"),
        )

    def test_explicit_occupations_beat_ai_as_the_product_or_subject_area(self):
        cases = [
            ("Senior AI Product Manager", "プロダクト管理"),
            ("AI Transformation - Program Manager", "プロジェクト・プログラム管理"),
            ("Risk, AI Model Validation, Vice President", "リスク管理"),
        ]
        for title, expected in cases:
            with self.subTest(title=title):
                self.assertEqual(classify_job({"title": title})["occupation"]["label"], expected)

    def test_trader_assistant_is_not_classified_as_a_trader(self):
        result = classify_job(
            {
                "title": "Trading Services Associate I",
                "description": "As a Trader Assistant in Prime brokerage services operations, you will support trading teams and trade capture.",
            }
        )
        self.assertEqual(result["occupation"]["label"], "オペレーション")

    def test_private_equity_is_alternative_asset_management_not_public_equity(self):
        self.assertEqual(
            labels("MSIM - Private Equity Solutions - Secondaries Associate")[:2],
            ("資産運用", "代替資産運用"),
        )

    def test_technology_affiliation_precedes_the_supported_trading_business(self):
        cases = [
            (
                "Executive Director - Sr. Technical Lead - Electronic Trading Platform",
                "電子取引システム",
            ),
            (
                "Engineering Lead | Equities Derivatives Technology | Executive Director",
                "株式・デリバティブ技術",
            ),
            (
                "Sr Director of Software Engineering Equity Derivatives Technology",
                "株式・デリバティブ技術",
            ),
            ("Lead Software Engineer - Rates Risk Engineer", "債券・金利・クレジット技術"),
        ]
        for title, subdepartment in cases:
            with self.subTest(title=title):
                self.assertEqual(
                    labels(title, department="Commercial & Investment Bank"),
                    ("Technology", subdepartment, "エンジニア・開発"),
                )
        result = classify_job({"title": cases[1][0], "department": "Corporate Sector"})
        self.assertEqual(result["department"]["label"], "Technology")
        self.assertEqual(result["department"]["basis"], "タイトル")

    def test_technology_coverage_and_quant_trading_are_not_engineering_affiliation(self):
        cases = [
            ("Investment Banking Vice President | Energy Technology", "投資銀行"),
            (
                "Relationship Executive - Innovation Economy Technology - Managing Director",
                "法人銀行",
            ),
            ("US Equity Research - Technology Hardware - Associate", "リサーチ"),
            # Technology risk is a technology function (decision P3, 2026-10-31).
            ("Technology Risk - Vice President - Security Architecture", "Technology"),
            ("Internal Audit, Technology Audit, Vice President", "コーポレート・共通部門"),
            ("GBM - Quantitative Rates Trading Strat, VP", "マーケッツ"),
        ]
        for title, department in cases:
            with self.subTest(title=title):
                self.assertEqual(classify_job({"title": title})["department"]["label"], department)

    def test_private_equity_engineering_keeps_its_asset_management_context(self):
        self.assertEqual(
            labels("Asset Management - Private Equity Software Engineer"),
            ("Technology", "資産運用技術", "エンジニア・開発"),
        )

    def test_explicit_technology_division_precedes_equity_title_but_partner_mentions_do_not(self):
        title = "Lead Equity Flow Derivatives Java Dev - Vice President"
        self.assertEqual(
            labels(
                title,
                description="You will build pricing systems. In the Technology division, we build applications.",
            ),
            ("Technology", "株式・デリバティブ技術", "エンジニア・開発"),
        )
        result = classify_job(
            {
                "title": "Equity Derivatives Associate",
                "description": "In the Technology division, we build the firm's applications.",
            }
        )
        self.assertEqual(result["department"]["label"], "Technology")
        self.assertEqual(result["department"]["basis"], "本文の職務記述")
        result = classify_job(
            {
                "title": "Fixed Income Institutional Sales",
                "description": "You will collaborate with engineers in the Technology division.",
            }
        )
        self.assertEqual(result["department"]["label"], "マーケッツ")

    def test_front_office_quant_developer_is_not_moved_to_its_technology_partner(self):
        result = classify_job(
            {
                "title": "Asset Management- Equities Quantitative Developer - VP/Associate",
                "department": "Asset & Wealth Management",
                "job_level": "Portfolio Management",
                "description": "Join our U.S. Disciplined Core Equity group. You will communicate daily with the Technology team.",
            }
        )
        self.assertEqual(result["department"]["label"], "資産運用")
        self.assertEqual(result["subdepartment"]["label"], "株式運用")
        self.assertEqual(result["occupation"]["label"], "エンジニア・開発")

    def test_explicit_technology_unit_and_public_engineering_category_are_evidence(self):
        for extra, basis in [
            ({"department": "Technology"}, "公開部門"),
            ({"job_level": "Software Engineering"}, "公開職務カテゴリ"),
            (
                {"description": "In the Technology division, we build the firm's applications."},
                "本文の職務記述",
            ),
        ]:
            with self.subTest(extra=extra):
                result = classify_job({"title": "Associate", **extra})
                self.assertEqual(result["department"]["label"], "Technology")
                self.assertEqual(result["department"]["basis"], basis)
                self.assertTrue(result["department"]["evidence"])

    def test_audited_keyword_errors_keep_their_neighbouring_labels(self):
        ccb = {"department": "Consumer & Community Banking"}
        awm = {"department": "Asset & Wealth Management"}
        cases = [
            (
                {"title": "Senior Home Lending Advisor - Suffolk County NY Branches", **ccb},
                "subdepartment",
                "住宅ローン",
            ),
            ({"title": "Private Client Banker - Manhattan", **ccb}, "subdepartment", "支店"),
            (
                {"title": "Vice President, Paid Social Automation and Innovation", **ccb},
                "subdepartment",
                "未分類",
            ),
            ({"title": "Chase Auto - Credit Analyst", **ccb}, "subdepartment", "自動車金融"),
            (
                {
                    "title": "Asset Management, Tax Smart Investment Specialist, Vice President",
                    **awm,
                },
                "department",
                "資産運用",
            ),
            ({"title": "Corporate Tax Manager"}, "occupation", "財務・経理・税務"),
            ({"title": "Associate, UX Designer – Equity Zen"}, "department", "未分類"),
            ({"title": "Equity Derivatives Trader"}, "department", "マーケッツ"),
            (
                {"title": "Quant Analytics, Senior Associate - Asset Wealth Management", **awm},
                "department",
                "資産運用・WM（横断）",
            ),
            (
                {"title": "J.P. Morgan Wealth Management – Private Client Advisor - Manhattan"},
                "occupation",
                "プライベートバンカー・FA",
            ),
            ({"title": "Private Client Banker - Manhattan", **ccb}, "occupation", "支店業務"),
            ({"title": "Client Advisor"}, "occupation", "営業・セールス"),
            (
                {"title": "Investment Banking Vice President | Energy Technology"},
                "subdepartment",
                "エネルギー・資源",
            ),
            (
                {"title": "Investment Banking - Technology, Media & Telecom - Associate"},
                "subdepartment",
                "テクノロジー・メディア・通信",
            ),
            (
                {"title": "Investment Banking - Media & Communications – Associate"},
                "occupation",
                "投資銀行バンカー",
            ),
            ({"title": "Corporate Communications Associate"}, "occupation", "マーケティング・広報"),
        ]
        for raw, key, expected in cases:
            with self.subTest(title=raw["title"], key=key):
                self.assertEqual(classify_job(raw)[key]["label"], expected)

    def test_decided_department_policies(self):
        ccb = {"department": "Consumer & Community Banking"}
        cib = {"department": "Commercial & Investment Bank"}
        cases = [
            # P1: Business Banking stays in retail for now.
            ({"title": "Business Banking Consultant Senior", **ccb}, ("リテール銀行", "中小企業")),
            ({"title": "Commercial Banking - Middle Market Banker", **cib}, ("法人銀行", None)),
            # P2: control and support functions inside a business count as corporate.
            (
                {"title": "Wealth Management Finance FP&A - Director"},
                ("コーポレート・共通部門", "財務・経理・税務"),
            ),
            (
                {"title": "Vice President, HR Business Advisor - Chase Wealth Management", **ccb},
                ("コーポレート・共通部門", "人事"),
            ),
            (
                {"title": "Wealth Management Privacy Risk Specialist"},
                ("コーポレート・共通部門", "リスク管理"),
            ),
            (
                {"title": "Senior Executive Administrative Assistant", **ccb},
                ("コーポレート・共通部門", "経営企画・管理"),
            ),
            (
                {"title": "Vice President - Valuation Risk Controller"},
                ("コーポレート・共通部門", "財務・経理・税務"),
            ),
            (
                {"title": "Treasury Sales Associate - Mid-Corporate Banking", **cib},
                ("法人銀行", None),
            ),
            (
                {"title": "Investment Banking - Leveraged Finance - Associate", **cib},
                ("投資銀行", None),
            ),
            (
                {"title": "Investment Banking Semiconductor Vice President - New York"},
                ("投資銀行", None),
            ),
            # P3: applied AI/ML teams and the CDAO count as Technology unless the title names a control function.
            ({"title": "Applied AI ML-Vice President", **ccb}, ("Technology", "AI・機械学習技術")),
            (
                {
                    "title": "Chief Data & Analytics Office Strategy, Associate",
                    "department": "Corporate Sector",
                },
                ("Technology", None),
            ),
            (
                {
                    "title": "AI/ML - Technology & Cybersecurity Risk Management - Compliance - Vice President"
                },
                ("コーポレート・共通部門", None),
            ),
        ]
        for raw, (department, subdepartment) in cases:
            with self.subTest(title=raw["title"]):
                result = classify_job(raw)
                self.assertEqual(result["department"]["label"], department)
                if subdepartment:
                    self.assertEqual(result["subdepartment"]["label"], subdepartment)

    def test_bofa_public_lines_of_business(self):
        cases = [
            ("Consumer & Small Business", "リテール銀行", None),
            ("Business Banking", "リテール銀行", "中小企業"),
            ("Global Research & Institute", "リサーチ", None),
            ("Global Operations", "コーポレート・共通部門", "オペレーション"),
            ("The CFO Group", "コーポレート・共通部門", "財務・経理・税務"),
            ("Chief People Organization", "コーポレート・共通部門", "人事"),
            ("Corporate Audit And Credit Review", "コーポレート・共通部門", "内部監査"),
            ("Global Risk Management", "コーポレート・共通部門", "リスク管理"),
            ("Enterprise Credit", "コーポレート・共通部門", "リスク管理"),
            ("Legal & Public Policy", "コーポレート・共通部門", "法務"),
            ("Global Markets", "マーケッツ", None),
            ("Global Corporate & Investment Banking", "投資銀行", None),
            ("Global Commercial Banking", "法人銀行", None),
            ("Global Payments Solutions", "決済・トランザクションバンキング", None),
            ("Merrill Wealth Management", "ウェルスマネジメント", None),
            ("Private Bank", "ウェルスマネジメント", None),
            ("Global Technology", "Technology", None),
        ]
        for public, department, subdepartment in cases:
            with self.subTest(public=public):
                result = classify_job({"title": "Associate", "department": public})
                self.assertEqual(result["department"]["label"], department)
                if subdepartment:
                    self.assertEqual(result["subdepartment"]["label"], subdepartment)

    def test_global_research_title_refines_the_cib_division(self):
        result = classify_job(
            {
                "title": "Global Research - U.S Economist - Associate",
                "department": "Commercial & Investment Bank",
            }
        )
        self.assertEqual(result["department"]["label"], "リサーチ")

    def test_risk_arbitrage_is_a_trading_desk(self):
        result = classify_job(
            {"title": "Risk Arbitrage Trader, Director", "department": "Institutional Trading"}
        )
        self.assertEqual(result["department"]["label"], "マーケッツ")
        self.assertEqual(result["occupation"]["label"], "トレーダー")

    def test_bofa_financial_centers_are_branches_of_the_consumer_bank(self):
        result = classify_job(
            {
                "title": "Financial Center Manager - 800 Sixth Avenue Financial Center",
                "department": "Consumer & Small Business",
            }
        )
        self.assertEqual(result["department"]["label"], "リテール銀行")
        self.assertEqual(result["subdepartment"]["label"], "支店")
        # The consumer bank's name alone does not make a job small-business banking.
        result = classify_job({"title": "Associate", "department": "Consumer & Small Business"})
        self.assertEqual(result["subdepartment"]["label"], "未分類")
        result = classify_job(
            {"title": "Small Business Banker", "department": "Consumer & Small Business"}
        )
        self.assertEqual(result["subdepartment"]["label"], "中小企業")

    def test_bofa_treasury_products_belong_to_payments_not_corporate_treasury(self):
        for title in ["Treasury Product Manager I", "Treasury Product Analyst - Payments"]:
            with self.subTest(title=title):
                result = classify_job({"title": title, "department": "Global Payments Solutions"})
                self.assertEqual(result["department"]["label"], "決済・トランザクションバンキング")

    def test_assistant_titles_name_the_occupation_before_the_team(self):
        result = classify_job(
            {
                "title": "Global Research Administrative Assistant",
                "department": "Global Research & Institute",
            }
        )
        self.assertEqual(result["occupation"]["label"], "秘書・事務サポート")

    def test_bofa_branch_and_coverage_titles(self):
        for title, occupation in [
            ("Financial Solutions Advisor - Bushwick Banking Center", "プライベートバンカー・FA"),
            ("Registered Wealth Management Client Associate", "顧客サービス"),
            ("J.P. Morgan Advisors - Senior Client Associate", "顧客サービス"),
            ("Market Financial Center Manager - Midtown", "支店業務"),
            ("Senior Banker", "営業・セールス"),
            ("Corporate Banker V", "営業・セールス"),
            ("Credit Officer II", "リスク管理"),
        ]:
            with self.subTest(title=title):
                self.assertEqual(classify_job({"title": title})["occupation"]["label"], occupation)

    def test_citi_job_family_groups_name_the_business(self):
        cases = [
            ("Consumer Sales", "リテール銀行", None),
            ("Customer Service", "リテール銀行", None),
            ("Private Client Coverage", "ウェルスマネジメント", None),
            ("Private Client Product Services", "ウェルスマネジメント", None),
            ("Institutional Sales", "マーケッツ", None),
            # Run 3 stored a few groups with the next field appended.
            ("Institutional Sales Job Family: Investor Sales", "マーケッツ", None),
            ("Institutional Trading Job Family: Trading", "マーケッツ", None),
            ("Institutional Banking", "投資銀行", None),
            ("Operations - Transaction Services", "コーポレート・共通部門", "オペレーション"),
            ("Operations - Services", "コーポレート・共通部門", "オペレーション"),
            (
                "Business Strategy, Management & Administration",
                "コーポレート・共通部門",
                "経営企画・管理",
            ),
            ("Communications and External Relations", "コーポレート・共通部門", "経営企画・管理"),
        ]
        for public, department, subdepartment in cases:
            with self.subTest(public=public):
                result = classify_job({"title": "Associate", "department": public})
                self.assertEqual(result["department"]["label"], department)
                if subdepartment:
                    self.assertEqual(result["subdepartment"]["label"], subdepartment)

    def test_treasury_trading_is_a_markets_desk(self):
        result = classify_job(
            {
                "title": "US Rates Strategist - Treasury Trading",
                "department": "Institutional Trading",
            }
        )
        self.assertEqual(result["department"]["label"], "マーケッツ")

    def test_citi_marketing_job_families_are_marketing(self):
        result = classify_job(
            {
                "title": "Vice President",
                "department": "Marketing",
                "job_level": "Advertising, Branding and Media",
            }
        )
        self.assertEqual(result["occupation"]["label"], "マーケティング・広報")

    def test_wealth_strategists_plan_for_clients(self):
        for title, public in [
            (
                "JPMorgan Wealth Management - Executive Director, Advanced Planner (Wealth Strategist)",
                "",
            ),
            ("Wealth Strategist", "Merrill Wealth Management"),
        ]:
            with self.subTest(title=title):
                result = classify_job({"title": title, "department": public})
                self.assertEqual(result["occupation"]["label"], "プライベートバンカー・FA")

    def test_portfolio_and_quantitative_risk_analytics_are_not_the_risk_function(self):
        for title in [
            "Area Product Owner, Quantitative Risk Analytics",
            "Quantitative Risk & Portfolio Analytics - Associate",
            "Global Investment Office - Institutional Portfolio & Risk Analytics, Vice President",
        ]:
            with self.subTest(title=title):
                self.assertNotEqual(
                    classify_job({"title": title})["department"]["label"], "コーポレート・共通部門"
                )
        for title, subdepartment in [
            ("Market Risk - Quantitative Risk Analyst - Vice President", "リスク管理"),
            (
                "Wholesale Credit Risk Controllers - Chief Financial Office - Vice President",
                "財務・経理・税務",
            ),
        ]:
            with self.subTest(title=title):
                result = classify_job({"title": title})
                self.assertEqual(result["department"]["label"], "コーポレート・共通部門")
                self.assertEqual(result["subdepartment"]["label"], subdepartment)

    def test_division_wide_awm_technology_is_not_wealth_technology(self):
        cases = [
            (
                "Asset & Wealth Management - Software Engineering - Associate - New York",
                "資産運用技術",
            ),
            ("Asset & Wealth Management - C++ Software Engineer - Vice President", "資産運用技術"),
            (
                "Private Wealth Management - Software Engineer - Vice President",
                "ウェルスマネジメント技術",
            ),
        ]
        for title, subdepartment in cases:
            with self.subTest(title=title):
                result = classify_job({"title": title})
                self.assertEqual(result["department"]["label"], "Technology")
                self.assertEqual(result["subdepartment"]["label"], subdepartment)

    def test_decided_occupation_labels(self):
        cases = [
            ("Associate Market Manager", "支店業務"),
            ("PWM Business Service Officer", "支店業務"),
            ("Estate Planning Strategist, Vice President", "プライベートバンカー・FA"),
            (
                "Quant Analytics, Senior Associate - Asset Wealth Management",
                "データ分析・データ管理",
            ),
            ("Quantitative Rates Strategist", "クオンツ・ストラテジスト"),
            (
                "U.S. Private Bank - Investment Specialist (GIO) - Vice President",
                "投資プロダクトスペシャリスト",
            ),
            ("Portfolio Manager - Fixed Income", "運用・ポートフォリオ管理"),
            ("Home Lending Underwriter", "融資・信用審査"),
            ("Content Design, Vice President", "デザイン・UX"),
            ("Senior Executive Administrative Assistant", "秘書・事務サポート"),
            ("Private Wealth Management Chief of Staff", "経営企画・管理"),
            ("Vice President, HR Business Advisor", "人事"),
        ]
        for title, role in cases:
            with self.subTest(title=title):
                self.assertEqual(classify_job({"title": title})["occupation"]["label"], role)


if __name__ == "__main__":
    unittest.main()
