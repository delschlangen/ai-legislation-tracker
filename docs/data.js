// AI Legislation Tracker - Bundled Data
// Last updated: 2024-12-24

const LEGISLATION_DATA = {
  federal: [
    {
      id: "fed-001",
      title: "Executive Order 14110 on Safe, Secure, and Trustworthy AI",
      type: "executive_order",
      status: "rescinded",
      date_issued: "2023-10-30",
      date_rescinded: "2025-01-20",
      issuing_body: "White House",
      summary: "Comprehensive AI executive order establishing safety requirements, reporting thresholds, and agency directives. Required frontier AI developers to share safety test results with government. Rescinded by subsequent administration.",
      key_provisions: [
        "Dual-use foundation model reporting requirements",
        "Compute threshold triggers (10^26 FLOP)",
        "NIST AI safety standards development",
        "Agency AI use case inventories",
        "AI talent immigration provisions"
      ],
      source_url: "https://www.whitehouse.gov/briefing-room/presidential-actions/2023/10/30/executive-order-on-the-safe-secure-and-trustworthy-development-and-use-of-artificial-intelligence/",
      tags: ["safety", "frontier_ai", "reporting", "compute_threshold"],
      last_verified: "2024-12-24",
      jurisdiction: "US Federal",
      jurisdiction_type: "federal"
    },
    {
      id: "fed-002",
      title: "NIST AI Risk Management Framework 1.0",
      type: "framework",
      status: "active",
      date_issued: "2023-01-26",
      issuing_body: "NIST",
      summary: "Voluntary framework for managing AI risks throughout the AI lifecycle. Organized around four core functions: Govern, Map, Measure, Manage.",
      key_provisions: [
        "Four core functions (Govern, Map, Measure, Manage)",
        "AI risk taxonomy",
        "Trustworthy AI characteristics",
        "Implementation guidance via Playbook"
      ],
      source_url: "https://www.nist.gov/itl/ai-risk-management-framework",
      tags: ["framework", "risk_management", "voluntary", "nist"],
      last_verified: "2024-12-24",
      jurisdiction: "US Federal",
      jurisdiction_type: "federal"
    },
    {
      id: "fed-003",
      title: "OMB Memorandum M-24-10: AI Governance",
      type: "guidance",
      status: "active",
      date_issued: "2024-03-28",
      issuing_body: "OMB",
      summary: "Requires federal agencies to implement AI governance structures, designate Chief AI Officers, and establish safeguards for rights-impacting and safety-impacting AI.",
      key_provisions: [
        "Chief AI Officer designation requirement",
        "AI use case inventories",
        "Rights-impacting AI safeguards",
        "Safety-impacting AI requirements",
        "Annual compliance reporting"
      ],
      source_url: "https://www.whitehouse.gov/omb/briefing-room/2024/03/28/omb-releases-implementation-guidance-following-president-bidens-executive-order-on-artificial-intelligence/",
      tags: ["federal_agencies", "governance", "chief_ai_officer", "safeguards"],
      last_verified: "2024-12-24",
      jurisdiction: "US Federal",
      jurisdiction_type: "federal"
    },
    {
      id: "fed-004",
      title: "Blueprint for an AI Bill of Rights",
      type: "guidance",
      status: "active",
      date_issued: "2022-10-04",
      issuing_body: "White House OSTP",
      summary: "Non-binding framework identifying five principles for AI systems: safe and effective systems, algorithmic discrimination protections, data privacy, notice and explanation, and human alternatives.",
      key_provisions: [
        "Safe and effective systems",
        "Algorithmic discrimination protections",
        "Data privacy",
        "Notice and explanation",
        "Human alternatives and fallback"
      ],
      source_url: "https://www.whitehouse.gov/ostp/ai-bill-of-rights/",
      tags: ["principles", "rights", "voluntary", "ostp"],
      last_verified: "2024-12-24",
      jurisdiction: "US Federal",
      jurisdiction_type: "federal"
    },
    {
      id: "fed-005",
      title: "SEC AI-Related Disclosure Guidance",
      type: "guidance",
      status: "active",
      date_issued: "2024-01-01",
      issuing_body: "SEC",
      summary: "Guidance on disclosure obligations related to AI risks and AI washing in public company filings.",
      key_provisions: [
        "Material AI risk disclosure",
        "AI washing enforcement priority",
        "MD&A discussion requirements"
      ],
      source_url: "https://www.sec.gov",
      tags: ["disclosure", "securities", "ai_washing", "sec"],
      last_verified: "2024-12-24",
      jurisdiction: "US Federal",
      jurisdiction_type: "federal"
    },
    {
      id: "fed-006",
      title: "FTC AI and Algorithm Enforcement",
      type: "enforcement_priority",
      status: "active",
      date_issued: "2023-01-01",
      issuing_body: "FTC",
      summary: "FTC enforcement focus on AI-related unfair and deceptive practices, including algorithmic discrimination and AI-enabled fraud.",
      key_provisions: [
        "Section 5 unfairness authority for AI harms",
        "AI claims substantiation requirements",
        "Algorithmic disgorgement remedy",
        "Commercial surveillance rulemaking"
      ],
      source_url: "https://www.ftc.gov/business-guidance/blog/2023/02/keep-your-ai-claims-check",
      tags: ["enforcement", "ftc", "consumer_protection", "discrimination"],
      last_verified: "2024-12-24",
      jurisdiction: "US Federal",
      jurisdiction_type: "federal"
    },
    {
      id: "fed-007",
      title: "DoD AI Adoption Strategy",
      type: "strategy",
      status: "active",
      date_issued: "2023-11-02",
      issuing_body: "Department of Defense",
      summary: "Strategy for accelerating DoD adoption of AI capabilities while maintaining ethical principles and safety standards.",
      key_provisions: [
        "AI adoption acceleration goals",
        "Responsible AI principles integration",
        "Workforce AI training requirements",
        "Industry partnership frameworks"
      ],
      source_url: "https://www.defense.gov",
      tags: ["defense", "adoption", "military", "dod"],
      last_verified: "2024-12-24",
      jurisdiction: "US Federal",
      jurisdiction_type: "federal"
    },
    {
      id: "fed-008",
      title: "Commerce Department AI Export Controls",
      type: "regulation",
      status: "active",
      date_issued: "2024-10-01",
      issuing_body: "Bureau of Industry and Security",
      summary: "Export controls on advanced AI chips and related technology to certain foreign countries, particularly China.",
      key_provisions: [
        "Advanced chip export restrictions",
        "Compute density thresholds",
        "Country-specific controls (China, Russia, Iran)",
        "Cloud computing restrictions"
      ],
      source_url: "https://www.bis.doc.gov",
      tags: ["export_controls", "chips", "china", "bis"],
      last_verified: "2024-12-24",
      jurisdiction: "US Federal",
      jurisdiction_type: "federal"
    }
  ],
  state: [
    {
      id: "state-001",
      state: "Colorado",
      bill_number: "SB 24-205",
      title: "Consumer Protections for Artificial Intelligence",
      status: "enacted",
      date_introduced: "2024-01-31",
      date_enacted: "2024-05-17",
      effective_date: "2026-02-01",
      summary: "First comprehensive state AI regulation in the US. Requires deployers and developers of high-risk AI systems to use reasonable care to avoid algorithmic discrimination.",
      key_provisions: [
        "High-risk AI system definition",
        "Developer duties (documentation, disclosure)",
        "Deployer duties (risk management, impact assessments)",
        "Consumer notification and opt-out rights",
        "Attorney General enforcement"
      ],
      source_url: "https://leg.colorado.gov/bills/sb24-205",
      tags: ["comprehensive", "high_risk", "discrimination", "first_state"],
      last_verified: "2024-12-24",
      jurisdiction: "Colorado",
      jurisdiction_type: "state"
    },
    {
      id: "state-002",
      state: "California",
      bill_number: "SB 1047",
      title: "Safe and Secure Innovation for Frontier AI Models Act",
      status: "vetoed",
      date_introduced: "2024-02-08",
      date_vetoed: "2024-09-29",
      summary: "Would have required safety testing and kill switch capabilities for frontier AI models above compute thresholds. Vetoed by Governor Newsom.",
      key_provisions: [
        "Compute threshold triggers ($100M training cost or 10^26 FLOP)",
        "Safety testing requirements",
        "Kill switch capability",
        "Whistleblower protections",
        "Frontier Model Division creation"
      ],
      veto_reason: "Governor cited concerns about applying strict standards to all AI models regardless of risk context",
      source_url: "https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202320240SB1047",
      tags: ["frontier_ai", "safety", "vetoed", "compute_threshold"],
      last_verified: "2024-12-24",
      jurisdiction: "California",
      jurisdiction_type: "state"
    },
    {
      id: "state-003",
      state: "California",
      bill_number: "AB 2013",
      title: "AI Training Data Transparency",
      status: "enacted",
      date_introduced: "2024-02-05",
      date_enacted: "2024-09-28",
      effective_date: "2026-01-01",
      summary: "Requires developers of generative AI systems to post documentation about training data on their websites.",
      key_provisions: [
        "Training data documentation requirement",
        "High-level summary of data sources",
        "Website publication requirement",
        "Applies to GenAI offered in California"
      ],
      source_url: "https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202320240AB2013",
      tags: ["transparency", "training_data", "disclosure", "genai"],
      last_verified: "2024-12-24",
      jurisdiction: "California",
      jurisdiction_type: "state"
    },
    {
      id: "state-004",
      state: "California",
      bill_number: "AB 2885",
      title: "AI Definition Standardization",
      status: "enacted",
      date_introduced: "2024-02-15",
      date_enacted: "2024-09-29",
      effective_date: "2025-01-01",
      summary: "Establishes standard definition of artificial intelligence for California law, aligned with NIST and federal definitions.",
      key_provisions: [
        "Standardized AI definition across CA code",
        "NIST alignment",
        "Applies to future AI legislation"
      ],
      source_url: "https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202320240AB2885",
      tags: ["definition", "standardization", "nist"],
      last_verified: "2024-12-24",
      jurisdiction: "California",
      jurisdiction_type: "state"
    },
    {
      id: "state-005",
      state: "Illinois",
      bill_number: "HB 3773",
      title: "AI Video Interview Act (Amendment)",
      status: "enacted",
      date_introduced: "2019-01-01",
      date_enacted: "2020-01-01",
      effective_date: "2020-01-01",
      summary: "First state law regulating AI in employment. Requires notice and consent for AI analysis of video interviews.",
      key_provisions: [
        "Notice to candidates before AI analysis",
        "Consent requirement",
        "Explanation of AI use",
        "Video deletion upon request"
      ],
      source_url: "https://www.ilga.gov/legislation/ilcs/ilcs3.asp?ActID=4015",
      tags: ["employment", "video_interview", "consent", "notice", "first_ai_law"],
      last_verified: "2024-12-24",
      jurisdiction: "Illinois",
      jurisdiction_type: "state"
    },
    {
      id: "state-006",
      state: "New York City",
      bill_number: "Local Law 144",
      title: "Automated Employment Decision Tools",
      status: "enacted",
      date_introduced: "2021-01-01",
      date_enacted: "2021-12-11",
      effective_date: "2023-07-05",
      summary: "Requires bias audits and notice for automated employment decision tools used in hiring in NYC.",
      key_provisions: [
        "Annual bias audit requirement",
        "Audit results publication",
        "Candidate notice requirements",
        "Alternative process availability"
      ],
      source_url: "https://www.nyc.gov/site/dca/about/automated-employment-decision-tools.page",
      tags: ["employment", "bias_audit", "local", "aedt"],
      last_verified: "2024-12-24",
      jurisdiction: "New York City",
      jurisdiction_type: "state"
    },
    {
      id: "state-007",
      state: "Texas",
      bill_number: "HB 2060",
      title: "AI Advisory Council",
      status: "enacted",
      date_introduced: "2023-03-09",
      date_enacted: "2023-06-18",
      effective_date: "2023-09-01",
      summary: "Creates advisory council to study AI use in state government and make recommendations.",
      key_provisions: [
        "Advisory council creation",
        "Study of AI in state government",
        "Annual report requirements",
        "Recommendations to legislature"
      ],
      source_url: "https://capitol.texas.gov/BillLookup/History.aspx?LegSess=88R&Bill=HB2060",
      tags: ["advisory", "state_government", "study"],
      last_verified: "2024-12-24",
      jurisdiction: "Texas",
      jurisdiction_type: "state"
    },
    {
      id: "state-008",
      state: "Utah",
      bill_number: "SB 149",
      title: "AI Policy Act",
      status: "enacted",
      date_introduced: "2024-01-16",
      date_enacted: "2024-03-13",
      effective_date: "2024-05-01",
      summary: "Creates AI learning lab and establishes disclosure requirements for generative AI interactions.",
      key_provisions: [
        "AI learning laboratory (regulatory sandbox)",
        "GenAI disclosure requirements",
        "Office of AI Policy creation",
        "State employee AI training"
      ],
      source_url: "https://le.utah.gov/~2024/bills/static/SB0149.html",
      tags: ["sandbox", "disclosure", "genai", "regulatory"],
      last_verified: "2024-12-24",
      jurisdiction: "Utah",
      jurisdiction_type: "state"
    },
    {
      id: "state-009",
      state: "Tennessee",
      bill_number: "HB 2959",
      title: "ELVIS Act (AI Voice Protection)",
      status: "enacted",
      date_introduced: "2024-01-01",
      date_enacted: "2024-03-21",
      effective_date: "2024-07-01",
      summary: "Protects artists from unauthorized AI-generated replicas of their voice and likeness.",
      key_provisions: [
        "Voice and likeness protection from AI",
        "Right of publicity expansion",
        "AI-specific provisions",
        "Music industry protections"
      ],
      source_url: "https://wapp.capitol.tn.gov/apps/BillInfo/default.aspx?BillNumber=HB2959",
      tags: ["voice", "likeness", "right_of_publicity", "music"],
      last_verified: "2024-12-24",
      jurisdiction: "Tennessee",
      jurisdiction_type: "state"
    },
    {
      id: "state-010",
      state: "Connecticut",
      bill_number: "SB 1103",
      title: "AI Inventory and Assessment",
      status: "enacted",
      date_introduced: "2023-01-01",
      date_enacted: "2023-06-07",
      effective_date: "2023-10-01",
      summary: "Requires state agencies to inventory AI systems and conduct impact assessments.",
      key_provisions: [
        "State agency AI inventory",
        "Impact assessments for high-risk AI",
        "Public reporting requirements",
        "Chief AI Officer consideration"
      ],
      source_url: "https://www.cga.ct.gov/asp/cgabillstatus/cgabillstatus.asp?selBillType=Bill&bill_num=SB1103",
      tags: ["state_government", "inventory", "impact_assessment"],
      last_verified: "2024-12-24",
      jurisdiction: "Connecticut",
      jurisdiction_type: "state"
    }
  ],
  international: [
    {
      id: "intl-001",
      jurisdiction: "European Union",
      name: "EU AI Act",
      title: "EU AI Act",
      type: "regulation",
      status: "enacted",
      date_adopted: "2024-03-13",
      date_effective: "2024-08-01",
      effective_date: "2026-08-01",
      full_application_date: "2026-08-01",
      summary: "World's first comprehensive AI regulation. Establishes risk-based framework with prohibited practices, high-risk system requirements, and transparency obligations.",
      key_provisions: [
        "Risk-based classification (unacceptable, high, limited, minimal)",
        "Prohibited AI practices (social scoring, real-time biometric ID)",
        "High-risk AI requirements (conformity assessment, CE marking)",
        "General-purpose AI model obligations",
        "Transparency requirements",
        "AI Office establishment"
      ],
      source_url: "https://eur-lex.europa.eu/eli/reg/2024/1689/oj",
      tags: ["comprehensive", "risk_based", "binding", "eu"],
      last_verified: "2024-12-24",
      jurisdiction_type: "international"
    },
    {
      id: "intl-002",
      jurisdiction: "United Kingdom",
      name: "UK AI Regulation Framework",
      title: "UK AI Regulation Framework",
      type: "framework",
      status: "active",
      date_adopted: "2024-02-06",
      summary: "Principles-based, sector-specific approach to AI regulation. Relies on existing regulators applying cross-cutting principles.",
      key_provisions: [
        "Five cross-cutting principles",
        "Sector regulator implementation",
        "Pro-innovation approach",
        "No new AI-specific regulator",
        "AI Safety Institute creation"
      ],
      source_url: "https://www.gov.uk/government/publications/ai-regulation-a-pro-innovation-approach",
      tags: ["principles", "sector_specific", "pro_innovation", "uk"],
      last_verified: "2024-12-24",
      jurisdiction_type: "international"
    },
    {
      id: "intl-003",
      jurisdiction: "China",
      name: "Interim Measures for Generative AI Services",
      title: "Interim Measures for Generative AI Services",
      type: "regulation",
      status: "active",
      date_adopted: "2023-07-13",
      date_effective: "2023-08-15",
      effective_date: "2023-08-15",
      summary: "Regulations governing generative AI services offered to the public in China. Emphasizes content control and socialist values.",
      key_provisions: [
        "Service provider registration",
        "Training data requirements",
        "Content labeling (AI-generated)",
        "Socialist core values alignment",
        "User real-name verification",
        "Algorithm filing requirements"
      ],
      source_url: "http://www.cac.gov.cn/2023-07/13/c_1690898327029107.htm",
      tags: ["genai", "content", "registration", "china"],
      last_verified: "2024-12-24",
      jurisdiction_type: "international"
    },
    {
      id: "intl-004",
      jurisdiction: "China",
      name: "Algorithm Recommendation Regulations",
      title: "Algorithm Recommendation Regulations",
      type: "regulation",
      status: "active",
      date_adopted: "2022-01-04",
      date_effective: "2022-03-01",
      effective_date: "2022-03-01",
      summary: "Regulations on algorithmic recommendations in internet services. Requires transparency and user controls.",
      key_provisions: [
        "Algorithm transparency requirements",
        "User opt-out rights",
        "Prohibition on price discrimination",
        "Labor protection provisions",
        "Algorithm registry"
      ],
      source_url: "http://www.cac.gov.cn/2022-01/04/c_1642894606364259.htm",
      tags: ["algorithms", "recommendations", "transparency", "china"],
      last_verified: "2024-12-24",
      jurisdiction_type: "international"
    },
    {
      id: "intl-005",
      jurisdiction: "Canada",
      name: "Artificial Intelligence and Data Act (AIDA)",
      title: "Artificial Intelligence and Data Act (AIDA)",
      type: "proposed_legislation",
      status: "pending",
      date_introduced: "2022-06-16",
      summary: "Part of Bill C-27. Would establish requirements for high-impact AI systems and prohibit certain AI practices.",
      key_provisions: [
        "High-impact system definition",
        "Risk assessment requirements",
        "Transparency obligations",
        "Prohibited conduct (serious harm)",
        "AI and Data Commissioner"
      ],
      source_url: "https://www.parl.ca/legisinfo/en/bill/44-1/c-27",
      tags: ["proposed", "high_impact", "comprehensive", "canada"],
      last_verified: "2024-12-24",
      jurisdiction_type: "international"
    },
    {
      id: "intl-006",
      jurisdiction: "Brazil",
      name: "AI Bill (PL 2338/2023)",
      title: "AI Bill (PL 2338/2023)",
      type: "proposed_legislation",
      status: "pending",
      date_introduced: "2023-05-03",
      summary: "Comprehensive AI bill establishing risk-based framework similar to EU AI Act.",
      key_provisions: [
        "Risk-based classification",
        "Fundamental rights protections",
        "High-risk AI requirements",
        "Regulatory sandbox provisions",
        "National AI authority"
      ],
      source_url: "https://www.camara.leg.br/propostas-legislativas/2358703",
      tags: ["proposed", "risk_based", "comprehensive", "brazil"],
      last_verified: "2024-12-24",
      jurisdiction_type: "international"
    },
    {
      id: "intl-007",
      jurisdiction: "OECD",
      name: "OECD AI Principles",
      title: "OECD AI Principles",
      type: "principles",
      status: "active",
      date_adopted: "2019-05-22",
      summary: "First intergovernmental standard on AI. Non-binding principles adopted by 46 countries.",
      key_provisions: [
        "Inclusive growth and sustainable development",
        "Human-centered values and fairness",
        "Transparency and explainability",
        "Robustness, security, and safety",
        "Accountability"
      ],
      source_url: "https://oecd.ai/en/ai-principles",
      tags: ["principles", "international", "non_binding", "oecd"],
      last_verified: "2024-12-24",
      jurisdiction_type: "international"
    },
    {
      id: "intl-008",
      jurisdiction: "United Nations",
      name: "UN Global Digital Compact (AI Provisions)",
      title: "UN Global Digital Compact (AI Provisions)",
      type: "resolution",
      status: "adopted",
      date_adopted: "2024-09-22",
      summary: "UN resolution including AI governance provisions, emphasizing international cooperation and capacity building.",
      key_provisions: [
        "International AI governance dialogue",
        "AI capacity building for developing nations",
        "Human rights in AI development",
        "Scientific cooperation"
      ],
      source_url: "https://www.un.org/techenvoy/global-digital-compact",
      tags: ["international", "un", "capacity_building", "cooperation"],
      last_verified: "2024-12-24",
      jurisdiction_type: "international"
    },
    {
      id: "intl-009",
      jurisdiction: "G7",
      name: "Hiroshima AI Process",
      title: "Hiroshima AI Process",
      type: "framework",
      status: "active",
      date_adopted: "2023-12-01",
      summary: "G7 framework establishing guiding principles and code of conduct for AI developers.",
      key_provisions: [
        "International guiding principles",
        "Voluntary code of conduct",
        "Advanced AI systems focus",
        "Interoperability commitments"
      ],
      source_url: "https://www.mofa.go.jp/ecm/ec/page5e_000076.html",
      tags: ["g7", "voluntary", "principles", "frontier_ai"],
      last_verified: "2024-12-24",
      jurisdiction_type: "international"
    },
    {
      id: "intl-010",
      jurisdiction: "International",
      name: "Bletchley Declaration",
      title: "Bletchley Declaration",
      type: "declaration",
      status: "active",
      date_adopted: "2023-11-01",
      summary: "Declaration from first global AI Safety Summit. 28 countries agreeing on frontier AI risks.",
      key_provisions: [
        "Frontier AI risk acknowledgment",
        "International cooperation commitment",
        "AI Safety Summit continuation",
        "Scientific collaboration"
      ],
      source_url: "https://www.gov.uk/government/publications/ai-safety-summit-2023-the-bletchley-declaration",
      tags: ["declaration", "safety", "frontier_ai", "international"],
      last_verified: "2024-12-24",
      jurisdiction_type: "international"
    }
  ]
};

// Combine all data into flat array
function getAllLegislation() {
  return [
    ...LEGISLATION_DATA.federal,
    ...LEGISLATION_DATA.state,
    ...LEGISLATION_DATA.international
  ];
}

// Get all unique tags with counts
function getTagCounts() {
  const tagCounts = {};
  getAllLegislation().forEach(item => {
    (item.tags || []).forEach(tag => {
      tagCounts[tag] = (tagCounts[tag] || 0) + 1;
    });
  });
  return Object.entries(tagCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);
}
