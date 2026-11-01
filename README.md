# global-esg-law

This repository records ESG-relevant law of the EU, the UK, India and the US as dated git history. It holds law text only where the matching row in `sources.json` has the verdict `pass`. Nothing in this repository says or implies that any company complies with any law.

The name is wider than what is built. Version 1 covers four jurisdictions (EU, GB, IN, US), listed below.

## What is covered (as of 2026-11-01)

"Stored" means the text is in `records/`, one file per version in force on a date. "Link only" means the instrument is listed with its official URL and no text is stored (permission requested, see `sources.json`).

### European Union (EU)

| Instrument | Held as |
|---|---|
| Directive (EU) 2022/2464 as regards corporate sustainability reporting (CSRD) | stored, 3 versions |
| Commission Delegated Regulation (EU) 2023/2772 supplementing Directive 2013/34/EU as regards sustainability reporting standards (ESRS) | stored, 1 version |
| Regulation (EU) 2020/852 on the establishment of a framework to facilitate sustainable investment (Taxonomy Regulation) | stored, 1 version |
| Regulation (EU) 2019/2088 on sustainability-related disclosures in the financial services sector (SFDR) | stored, 4 versions |
| Directive (EU) 2024/1760 on corporate sustainability due diligence (CSDDD) | stored, 3 versions |
| Directive (EU) 2025/794 amending Directives (EU) 2022/2464 and (EU) 2024/1760 as regards the dates from which Member States are to apply certain corporate sustainability reporting and due diligence requirements | stored, 1 version |
| Directive (EU) 2026/470 amending Directives 2006/43/EC, 2013/34/EU, (EU) 2022/2464 and (EU) 2024/1760 as regards certain corporate sustainability reporting requirements and certain corporate sustainability due diligence requirements | stored, 1 version |
| Commission Delegated Regulation (EU) 2025/1416 amending Delegated Regulation (EU) 2023/2772 as regards the postponement of the date of application of the disclosure requirements for certain undertakings | stored, 1 version |
| Commission Delegated Regulation (EU) 2026/1563 amending Delegated Regulation (EU) 2023/2772 as regards the simplification of certain sustainability reporting standards | stored, 1 version |
| Commission Delegated Regulation (EU) 2021/2139 establishing technical screening criteria for climate change mitigation and adaptation under the Taxonomy Regulation (Climate Delegated Act) | stored, 6 versions |
| Commission Delegated Regulation (EU) 2021/2178 specifying the content and presentation of Taxonomy disclosures by undertakings subject to Articles 19a or 29a of Directive 2013/34/EU (Disclosures Delegated Act) | stored, 4 versions |
| Commission Delegated Regulation (EU) 2022/1214 amending Delegated Regulations (EU) 2021/2139 and (EU) 2021/2178 as regards economic activities in certain energy sectors (Complementary Climate Delegated Act) | stored, 1 version |
| Commission Delegated Regulation (EU) 2023/2486 establishing technical screening criteria for water, circular economy, pollution prevention and biodiversity under the Taxonomy Regulation (Environmental Delegated Act) | stored, 2 versions |
| Commission Delegated Regulation (EU) 2023/2485 amending Delegated Regulation (EU) 2021/2139 with additional technical screening criteria for certain economic activities | stored, 1 version |
| Commission Delegated Regulation (EU) 2026/73 amending Delegated Regulations (EU) 2021/2178, 2021/2139 and 2023/2486 as regards simplification of Taxonomy disclosures and of certain technical screening criteria | stored, 1 version |
| Commission Delegated Regulation (EU) 2022/1288 supplementing Regulation (EU) 2019/2088 with regulatory technical standards on sustainability-related disclosures (SFDR RTS) | stored, 2 versions |

### United Kingdom (GB)

| Instrument | Held as |
|---|---|
| Companies Act 2006, section 414CB (non-financial and sustainability information statement) | stored, 2 versions |
| Companies Act 2006, Part 15 Chapter 4A, strategic report (sections 414A to 414D) | stored, 7 versions |
| The Companies (Strategic Report) (Climate-related Financial Disclosure) Regulations 2022 | stored, 1 version |
| FCA ESG sourcebook: Sustainability Disclosure Requirements, investment labels and anti-greenwashing rule (PS23/16) | link only |
| UK Sustainability Reporting Standards: UK SRS S1 General Requirements and UK SRS S2 Climate-related Disclosures | link only |

### India (IN)

| Instrument | Held as |
|---|---|
| Companies Act, 2013, section 135 (corporate social responsibility) | link only |
| SEBI (Listing Obligations and Disclosure Requirements) Regulations, 2015, regulation 34(2)(f) (business responsibility and sustainability report) | link only |
| SEBI circular: Business responsibility and sustainability reporting by listed entities (SEBI/HO/CFD/CMD-2/P/CIR/2021/562) | link only |
| SEBI circular: BRSR Core, framework for assurance and ESG disclosures for value chain (SEBI/HO/CFD/CFD-SEC-2/P/CIR/2023/122) | link only |
| SEBI circular: Measures to facilitate ease of doing business with respect to framework for assurance or assessment, ESG disclosures for value chain, and voluntary disclosure on green credits (SEBI/HO/CFD/CFD-PoD-1/P/CIR/2025/42) | link only |

### United States (US)

| Instrument | Held as |
|---|---|
| The Enhancement and Standardization of Climate-Related Disclosures for Investors (SEC Release 33-11275) | stored, 1 version |
| Mandatory Greenhouse Gas Reporting (EPA, 40 CFR Part 98) | stored, 27 versions |
| California Climate Corporate Data Accountability Act (SB 253), Health and Safety Code 38532 | stored, 2 versions |
| California Climate-Related Financial Risk Act (SB 261), Health and Safety Code 38533 | stored, 2 versions |
| California SB 219 (amends Health and Safety Code 38532 and 38533) | stored, 1 version |

## Look up the law in force on a date

```
python3 tools/law.py <ISO2> <YYYY-MM-DD>
```

Example: `python3 tools/law.py GB 2023-01-01`. Options: `[--repo PATH] [--ref history] [--json]`. In Python: `in_force(iso2, on, repo=ROOT, ref="history") -> list[dict]`. The lookup reads the `history` branch, which holds one dated commit per record with the text in it. Stayed or enjoined rules count as in force on their date; their `status_note` from `register/<ISO2>/scope.json` is printed with them. `tools/law.py` ships with GEL-01-07; this interface is fixed in the readiness report for that story.

## Rebuild the history

```
python3 tools/build.py --branch history
```

This builds `history` from scratch from `records/` and replaces the branch if it exists.

## Tests

```
python3 -m pytest tests -q
```

Python 3.11 or later, standard library plus git. pytest is the only extra.

## Before going public

The repository is private and stays private until Varun decides otherwise. Before that decision, run all three and read the output:

```
python3 tools/check_corpus.py
python3 tools/publish_gate.py
python3 -m pytest tests -q
```

`check_corpus.py` refuses any record whose source row is not `pass`. `publish_gate.py` prints every source row and scope entry and exits non-zero if an entry is `pending`, a stored entry has no record or a source row that is not `pass`, or a link-only entry has records. Today every source row is `pass` or `permission requested`, and every instrument with a `permission requested` row is link only.

Size as of 2026-11-01: `records/` is about 72 MB.
