"""Conservative, inspectable business and occupation labels for the HTML report.

These are analytical labels, not a claim about a bank's official organization.
Organizational function takes precedence over the business a system supports.
Broad public divisions remain broad and generic firm descriptions are never
treated as a job's team.
"""

import html
import re

VERSION = "2026-10-31.6"
UNKNOWN = "未分類"
TECHNICAL_ROLE = (
    r"software\s*(?:engineering|development|architect)|\bengineer\b|\bdeveloper\b|"
    r"engineering (?:manager|lead|director)|(?:technical|technology) lead|site reliability|"
    r"\b(?:java|c\+\+|c#|python|scala|backend|frontend|full.stack) dev\b"
)


def has(pattern, text):
    return bool(re.search(pattern, text, re.IGNORECASE))


def label(value=UNKNOWN, basis="情報不足", evidence=""):
    return {"label": value, "basis": basis, "evidence": evidence[:280]}


CORPORATE = (
    (r"\blegal\b|\battorney\b|\bcounsel\b", "法務"),
    (r"internal audit|corporate audit|^audit\b", "内部監査"),
    (r"compliance|financial crimes|anti.money laundering|\bAML\b", "コンプライアンス"),
    (
        r"human (?:capital|resources)|\bHCM\b|\bHR\b|recruit|talent (?:acquisition|(?:&|and) performance)|learning (?:&|and) development|skills training|"
        r"chief people",
        "人事",
    ),
    (
        # Portfolio and quantitative risk analytics serve investment teams, not the risk function.
        r"(?<!portfolio & )(?<!portfolio and )(?<!quantitative )\brisk\b"
        r"(?! (?:trader|trading|taker|controller|arbitrage))(?! (?:&|and) portfolio analytics)|"
        r"controls? (?:&|and) governance|\bconduct\b",
        "リスク管理",
    ),
    (
        r"corporate treasury|controllers?|\bvaluation control\b|\btax\b(?![- ](?:smart|aware|managed|efficient))|^finance\b|finance (?:&|and) business management|\bF&BM\b|business manag(?:er|ement)|"
        r"planning (?:&|and) analysis|\bP&A\b|\bFP&A\b|global finance\b|(?:management|business) finance\b|"
        r"\bfinance[ ,-]+(?:FP&A|strategy|reporting)|treasury(?! (?:services|sales|product|trading|management services|solutions))|"
        r"financial (?:reporting|analysis\b|analyst)|sales compensation|\bCFO group\b",
        "財務・経理・税務",
    ),
    (
        r"^corporate (?:strategy|communications)|^office of the|public relations|internal communications|"
        r"administrative assistant|executive assistant",
        "経営企画・管理",
    ),
    # BofA's operations and credit lines of business, named as the whole public field only.
    (r"^global operations$", "オペレーション"),
    (r"^enterprise credit$", "リスク管理"),
    # Citi's job family groups (run 3 stored a few with the next field appended).
    (r"^operations - (?:transaction )?services\b", "オペレーション"),
    (
        r"^(?:business strategy, management (?:&|and) administration|communications and external relations)\b",
        "経営企画・管理",
    ),
)

# Citi's job family groups name the business; a title that starts with one means the same.
CITI_GROUPS = (
    (r"^(?:consumer sales|customer service)\b", "リテール銀行"),
    (r"^private client (?:coverage|product services)\b", "ウェルスマネジメント"),
    (r"^institutional (?:sales|trading)\b", "マーケッツ"),
    (r"^institutional banking\b", "投資銀行"),
)


def corporate_function(text):
    return next((name for pattern, name in CORPORATE if has(pattern, text)), None)


def business(text):
    """Prefer explicit business names over product words within those names."""
    if not text:
        return UNKNOWN
    if corporate_function(text) or has(r"corporate sector", text):
        return "コーポレート・共通部門"
    if has(
        r"investment bank(?:ing|er)\b|\bIBD\b|\bM\s*&\s*A\b|mergers?\s*(?:&|and)\s*acquisitions?|(?:equity|debt) capital markets|leveraged finance",
        text,
    ):
        return "投資銀行"
    if has(
        r"associate banker|relationship banker|private client banker|\bbranch\b|home lending|mortgage (?:advisor|banker|loan)",
        text,
    ):
        return "リテール銀行"
    # AWM alone is broad; an explicitly named private bank/AM team refines it.
    awm = has(r"asset\s*(?:&|and)?\s*wealth management|\bAWM\b", text)
    if has(
        r"private bank(?:ing|er)?\b|private wealth|financial advis[eo]r|wealth advis[eo]r|family office",
        text,
    ):
        return "ウェルスマネジメント"
    if not awm and has(r"wealth management", text):
        return "ウェルスマネジメント"
    if has(r"(?<!wealth )asset management|investment management|\bMSIM\b|\bGSAM\b", text):
        return "資産運用"
    if awm:
        return "資産運用・WM（横断）"
    if has(
        r"global (?:investment )?research|(?:equity|equities|credit|economics?|macro) research",
        text,
    ):
        return "リサーチ"
    if has(r"payments?|transaction banking|treasury services", text):
        return "決済・トランザクションバンキング"
    if has(r"securities services|custody|fund serv(?:ices|icing)|fund svcs", text):
        return "証券サービス"
    if has(r"business bank", text):
        return "リテール銀行"
    if has(
        r"commercial bank|corporate bank|relationship executive|middle market bank",
        text,
    ):
        return "法人銀行"
    if has(
        r"global markets|\bGBM\s*[-–,|]?\s*public\b|\bFICC\b|fixed income|(?<!private )\bequit(?:y|ies)\b(?!\s*zen\b)|\bFX\b|foreign exchange|\brates\b|commodit(?:y|ies)|securiti[sz]ed|\btrader\b|\btrading\b|sales.institutional",
        text,
    ):
        return "マーケッツ"
    if has(
        r"global banking\s*(?:&|and)\s*markets|\bGBM\b|(?:commercial|corporate)\s*(?:&|and)\s*investment bank|\bCIB\b",
        text,
    ):
        return "投資銀行・マーケッツ（横断）"
    if has(
        r"consumer\s*(?:&|and)\s*(?:community bank|small business)|consumer bank|retail bank", text
    ):
        return "リテール銀行"
    return next((name for pattern, name in CITI_GROUPS if has(pattern, text)), UNKNOWN)


def technology_affiliation(title, public, category, contexts, description):
    """Do not mistake a trading system's users for its engineers' department."""
    text = re.sub(r"<[^>]+>", " ", html.unescape(description or ""))
    text = re.sub(r"\s+", " ", text)
    # This is an introduction of the job's division, not a reference to a
    # technology partner in the middle of a responsibility/requirements sentence.
    match = re.search(
        r"(?:^|[.!?]\s+)\s*(?P<unit>(?:in|within) (?:the|our) (?:global )?(?:technology|engineering) (?:division|department))\b",
        text,
        re.IGNORECASE,
    )
    if match:
        return label("Technology", "本文の職務記述", match.group("unit"))
    # Quant developers can belong to an investment/trading team. An explicit
    # technology unit/category can establish affiliation; the role alone cannot.
    quant_developer = (
        has(r"\bquant(?:itative)?\b|\bQTR\b", title)
        and has(r"\bdeveloper\b|\bdev\b", title)
        and not has(r"software engineer|technical lead|engineering lead", title)
    )
    # Technology risk, the CDAO and applied AI/ML teams are technology functions
    # unless the title names a corporate control function such as HR or compliance.
    if has(r"\btech(?:nology)? risk\b|\brisk tech(?:nology)?\b", title) or (
        has(
            r"applied ai|\bAI/ML\b|\bAIML\b|machine learning|chief data (?:&|and) analytics|\bCDAO\b",
            title,
        )
        and not corporate_function(title)
    ):
        return label("Technology", "タイトル", title)
    if (has(TECHNICAL_ROLE, title) and not quant_developer) or has(
        r"(?:^|[|,–-])\s*(?:the core )?engineering\s*(?:[|,–-]|$)", title
    ):
        return label("Technology", "タイトル", title)
    if re.fullmatch(
        r"(?:global )?(?:technology|engineering)(?: division| department)?", public, re.IGNORECASE
    ):
        return label("Technology", "公開部門", public)
    if has(TECHNICAL_ROLE, category) or re.fullmatch(
        r"(?:software|data|infrastructure|security|network) engineering|architecture|cybersecurity(?: operations)?",
        category,
        re.IGNORECASE,
    ):
        return label("Technology", "公開職務カテゴリ", category)
    if business(title) == UNKNOWN:
        for context, role in contexts:
            if has(TECHNICAL_ROLE, role) and not quant_developer:
                return label("Technology", "本文の職務記述", context)
    return None


def subbusiness(department, text):
    if department == "Technology":
        rules = (
            # "Asset & Wealth Management" names the whole division, not its wealth business.
            (
                r"private wealth|\bPWM\b|private bank|(?<!asset & )(?<!asset and )(?<!asset )wealth",
                "ウェルスマネジメント技術",
            ),
            (
                r"asset management|investment management|\bMSIM\b|\bGSAM\b|private equity|"
                r"asset\s*(?:&|and)?\s*wealth management|\bAWM\b",
                "資産運用技術",
            ),
            (r"payments?|transaction banking", "決済システム"),
            (r"\bequit(?:y|ies)\b|prime (?:brokerage|services)", "株式・デリバティブ技術"),
            (
                r"fixed income|\brates\b|\bcredit\b|securiti[sz]ed|\bbonds?\b",
                "債券・金利・クレジット技術",
            ),
            (r"\bFX\b|foreign exchange|\bFICC\b", "為替・FICC技術"),
            (r"electronic trading|algo trading|trading platform", "電子取引システム"),
            (r"front office|global banking\s*(?:&|and)\s*markets", "フロントオフィス技術"),
            (r"cyber|security", "サイバーセキュリティ"),
            (r"data engineer|data platform", "データ基盤"),
            (r"\bAI\b|machine learning|\bLLM\b", "AI・機械学習技術"),
            (r"infrastructure|cloud|network|site reliability", "基盤・クラウド"),
            (r"software|application", "アプリケーション開発"),
        )
        return next((name for pattern, name in rules if has(pattern, text)), UNKNOWN)
    if department == "コーポレート・共通部門":
        return corporate_function(text) or (
            "テクノロジー"
            if has(r"software|engineer|technology|developer|cyber", text)
            else UNKNOWN
        )
    if department == "投資銀行":
        rules = (
            (r"public finance|municipal", "公共・インフラ金融"),
            (r"\bM\s*&\s*A\b|mergers?\s*(?:&|and)\s*acquisitions?|secondaries", "M&A"),
            (r"equity capital markets|\bECM\b", "株式資本市場（ECM）"),
            (
                r"debt capital markets|\bDCM\b|leveraged finance|acquisition finance",
                "債券・レバレッジドファイナンス",
            ),
            (r"financial institutions|\bFIG\b|fintech", "金融機関・FinTech"),
            (r"healthcare|health care", "ヘルスケア"),
            (r"energy|power|natural resources", "エネルギー・資源"),
            (r"technology|\bTMT\b|media|telecom", "テクノロジー・メディア・通信"),
            (r"real estate|gaming|lodging", "不動産"),
            (r"industrials", "インダストリアル"),
            (r"consumer|retail", "消費財・小売"),
        )
    elif department == "マーケッツ":
        equity = has(r"\bequit(?:y|ies)\b|prime (?:brokerage|services)|\bdelta one\b", text)
        ficc = has(r"\bFICC\b", text)
        fixed = has(
            r"fixed income|\brates\b|\bcredit\b|securiti[sz]ed|\bbonds?\b|mortgage|municipal", text
        )
        fx = has(r"\bFX\b|foreign exchange|currenc(?:y|ies)", text)
        commodity = has(r"commodit(?:y|ies)", text)
        if equity and (ficc or fixed or fx or commodity):
            return "商品横断（FICC・株式）"
        if equity:
            return "株式部"
        if sum([fixed, fx, commodity]) > 1:
            return "FICC（商品横断）"
        if fx:
            return "為替部"
        if commodity:
            return "商品部"
        if fixed:
            return "債券部"
        return "FICC（商品横断）" if ficc else UNKNOWN
    elif department == "資産運用":
        rules = (
            (r"multi.asset", "マルチアセット運用"),
            (
                r"private markets|private equity|private credit|private debt|alternatives|hedge fund|real estate",
                "代替資産運用",
            ),
            (r"fixed income|\bcredit\b|\brates\b|\bbonds?\b", "債券運用"),
            (r"\bequit(?:y|ies)\b", "株式運用"),
            (r"liquidity|money market", "流動性・短期運用"),
            (r"solutions|multi.asset", "運用ソリューション"),
        )
    elif department == "ウェルスマネジメント":
        rules = (
            (r"private bank", "プライベートバンク"),
            (r"private wealth|ultra.high|family office", "富裕層・ファミリーオフィス"),
            (r"financial advis|wealth advis", "ファイナンシャルアドバイザリー"),
            (r"lending|mortgage", "融資"),
            (r"investment|portfolio", "投資・ポートフォリオ"),
        )
    elif department == "法人銀行":
        rules = (
            (r"innovation economy|venture|start.up", "イノベーション企業"),
            (r"business bank|small business", "中小企業"),
            (r"middle market|mid.corporate", "中堅企業"),
            (r"financial institutions|\bFIG\b", "金融機関"),
            (r"real estate", "不動産"),
        )
    elif department == "決済・トランザクションバンキング":
        rules = (
            (r"broker.dealers?|financial institutions|\bFIG\b", "金融機関向け決済"),
            (r"merchant", "加盟店決済"),
            (r"trade|working capital", "貿易金融・運転資金"),
            (r"liquidity|cash management", "流動性・キャッシュマネジメント"),
            (r"transaction banking", "トランザクションバンキング"),
        )
    elif department == "リテール銀行":
        rules = (
            (r"home lending|mortgage", "住宅ローン"),
            (
                r"branch|associate banker|relationship banker|private client banker|financial center|banking center",
                "支店",
            ),
            (r"card", "カード"),
            (r"\bauto(?:motive)?\b", "自動車金融"),
            # BofA's consumer bank is named "Consumer & Small Business".
            (r"business bank|(?<!consumer & )(?<!consumer and )small business", "中小企業"),
        )
    elif department == "証券サービス":
        rules = (
            (r"lending|financing", "証券貸借・ファイナンス"),
            (r"fund", "ファンドサービス"),
            (r"custody", "カストディ"),
        )
    elif department == "リサーチ":
        rules = (
            (r"\bequit(?:y|ies)\b", "株式リサーチ"),
            (r"credit|fixed income", "債券・クレジットリサーチ"),
            (r"economics?|macro", "経済・マクロリサーチ"),
        )
    else:
        return UNKNOWN
    return next((name for pattern, name in rules if has(pattern, text)), UNKNOWN)


OCCUPATIONS = (
    # An assistant's title names the occupation before the team supported.
    (r"administrative assistant|executive assistant", "秘書・事務サポート"),
    (
        TECHNICAL_ROLE + r"|cybersecurity",
        "エンジニア・開発",
    ),
    (r"product (?:manager|management|owner)|product development", "プロダクト管理"),
    (r"project manag|program manag|project execution", "プロジェクト・プログラム管理"),
    (r"^risk\b(?! arbitrage)|model validation|model risk", "リスク管理"),
    (r"trader assistant|trading assistant|trading services", "オペレーション"),
    (
        r"data scien|machine learning|artificial intelligence|\bAI\b|predictive science",
        "データサイエンス・AI",
    ),
    (
        r"quant(?:itative)? analytics|data analyst|business intelligence|data (?:governance|lineage|management)\b|data owner",
        "データ分析・データ管理",
    ),
    (
        r"estate planning|wealth plann(?:er|ing)|financial planner|wealth strategist",
        "プライベートバンカー・FA",
    ),
    (r"quantitative|\bquant\b|\bstrats?\b|strategist", "クオンツ・ストラテジスト"),
    (r"\battorney\b|\bcounsel\b|\blegal\b", "法務"),
    (r"internal audit|\bauditor\b|^audit\b", "内部監査"),
    (r"compliance|financial crimes|anti.money laundering|\bAML\b", "コンプライアンス"),
    (r"human (?:resources|capital)|\bHCM\b|\bHR\b|recruit|talent acquisition", "人事"),
    (
        r"controllers?|valuation control|\baccountant\b|accounting|\btax\b(?![- ](?:smart|aware|managed|efficient))|financial reporting|finance (?:manager|analyst)",
        "財務・経理・税務",
    ),
    (r"\boperations?\b|trade support|settlements?|loan servicing", "オペレーション"),
    (r"sales[ -]?trader|sales[ -]?trading", "セールストレーダー"),
    (r"\btrader\b|algo trading|systematic trading|financing trading", "トレーダー"),
    (r"structur(?:er|ing)", "ストラクチャラー"),
    (r"investment specialist|client portfolio manag", "投資プロダクトスペシャリスト"),
    (r"underwriter|loan officer", "融資・信用審査"),
    (
        r"portfolio manag|investment manager|fund manag",
        "運用・ポートフォリオ管理",
    ),
    (
        r"private banker\b|financial advis[eo]r|wealth advis[eo]r|private client advis[eo]r|financial solutions advis[eo]r",
        "プライベートバンカー・FA",
    ),
    (r"research", "リサーチ"),
    (
        r"\bsales\b|relationship (?:executive|manager)|client (?:advisor|adviser)|client sales|(?:senior|corporate|commercial) banker\b",
        "営業・セールス",
    ),
    (r"\brisk\b|model validation|credit officer", "リスク管理"),
    (
        r"associate banker|relationship banker|private client banker|branch manag|\bmarket manager\b|business service officer|financial center manag",
        "支店業務",
    ),
    (r"client service|customer service|client support|client associate", "顧客サービス"),
    (
        r"\bUX\b|user experience|(?:content|experience|conversation(?:al)?|product|visual|graphic|interaction) design|designer\b|art director",
        "デザイン・UX",
    ),
    (
        r"marketing|advertising|branding|(?<!media & )(?<!media and )\bcommunications\b",
        "マーケティング・広報",
    ),
    (
        r"business manag|business strategy|strategic planning|chief of staff|chief administrative",
        "経営企画・管理",
    ),
)


def occupation(text, department):
    found = next((name for pattern, name in OCCUPATIONS if has(pattern, text)), None)
    if found:
        return found
    # An explicitly named trading role can omit the word "Trader". Apply this
    # after other functions so the same desk's support roles remain distinct.
    if department == "マーケッツ" and has(r"\bxva[ -]+trading\b", text):
        return "トレーダー"
    if department == "投資銀行" and has(
        r"investment bank|\bM\s*&\s*A\b|capital markets|mergers?", text
    ):
        return "投資銀行バンカー"
    return UNKNOWN


def role_contexts(description):
    """Only explicit job/team introductions, never the full firm boilerplate."""
    text = re.sub(r"<[^>]+>", " ", html.unescape(description or ""))
    text = re.sub(r"\s+", " ", text)
    introductions = []
    for match in re.finditer(
        r"\bAs (?:an?|the) (?P<role>[^,.;!?]{3,100}?)(?: (?:within|in|on) [^,.;!?]{3,140})?(?=,\s*(?:you|your)\b|\s+you will\b)",
        text,
        re.IGNORECASE,
    ):
        introductions.append((match.start(), match.group(0), match.group("role")))
    for match in re.finditer(
        r"\b(?:join|joining) (?:the|our) [^.;!?]{5,180}?(?:team|desk|group)\b|\b(?:The|Our) [^.;!?]{3,120}?(?:department|division|desk)\b",
        text,
        re.IGNORECASE,
    ):
        # Team membership alone does not establish the individual's occupation.
        introductions.append((match.start(), match.group(0), ""))
    for _, context, role in sorted(introductions):
        yield context, role


def classify_job(raw):
    title = raw.get("title") or ""
    public = raw.get("department") or ""
    category = raw.get("job_level") or ""
    contexts = list(role_contexts(raw.get("description")))
    department = technology_affiliation(title, public, category, contexts, raw.get("description"))
    # A narrow title can refine a broad public division. A Corporate Sector
    # assignment is kept when an embedded product word names the supported desk.
    candidates = [(title, "タイトル"), (public, "公開部門")]
    if has(r"corporate sector", public):
        candidates.reverse()
    candidates.extend((text, "本文の職務記述") for text, _ in contexts)
    for text, basis in candidates:
        if department is not None:
            break
        found = business(text)
        if found != UNKNOWN:
            department = label(found, basis, text)
            break
    department = department or label()
    subdepartment = label()
    for text, basis in [
        (title, "タイトル"),
        (public, "公開部門"),
        *[(c, "本文の職務記述") for c, _ in contexts],
    ]:
        # A body team belonging to another business cannot refine a known one.
        if (
            basis == "本文の職務記述"
            and business(text) not in (UNKNOWN, department["label"])
            and not (department["label"] == "Technology" and has(TECHNICAL_ROLE, text))
        ):
            continue
        found = subbusiness(department["label"], text)
        if found != UNKNOWN:
            subdepartment = label(found, basis, text)
            break
    role = label()
    for text, basis, evidence in [
        (title, "タイトル", title),
        (category, "公開職務カテゴリ", category),
        *[(role, "本文の職務記述", c) for c, role in contexts if role],
    ]:
        found = occupation(text, department["label"])
        if found != UNKNOWN:
            role = label(found, basis, evidence)
            break
    return {"department": department, "subdepartment": subdepartment, "occupation": role}
