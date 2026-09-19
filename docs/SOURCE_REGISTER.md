# Source register

<!-- Generated from data/source-register.json by scripts/render_source_register.py. Edit the JSON, not this file. -->

- **Prepared:** 2026-09-19
- **Scope:** Pilot: Abuja, AMAC and Bwari Area Councils
- **Machine-readable register:** [`data/source-register.json`](../data/source-register.json), checked by `python3 scripts/validate_source_register.py --self-test`.

This is the evidence baseline for the six seed projects. Nothing here is a finding about any person or organisation. A fact is what one named source says, at the recorded date.

## Method

Each source was requested once on the retrieval date. A passage counts as verified only if it appears, word for word, in the visible text of the retrieved page (tags removed, whitespace collapsed). raw_page_sha256 hashes the exact bytes received and will differ if the site changes its markup; the passage hash is the stable evidence. Sources that blocked the request were not bypassed.

Source availability is recorded on each source and is separate from whether a fact is verified. All incident reports are fictional and labelled.

## Summary

| Project | Sources read | Facts with an exact verified passage | Facts not verified |
| --- | --- | --- | --- |
| AMAC-01 Saburi I and II Access Road | 1 of 1 | 1 | 0 |
| AMAC-02 Karshi Model Smart School | 0 of 1 | 0 | 1 |
| AMAC-03 Junior Secondary School, Lokogoma: toilets and desks | 0 of 1 | 0 | 1 |
| BWARI-01 Bwari Township Water Supply Network | 1 of 1 | 2 | 0 |
| BWARI-02 Gaba-Tokulo Road | 2 of 2 | 4 | 0 |
| BWARI-03 Bwari Town Primary Health Center, Kuduru | 0 of 1 | 0 | 1 |

## Sources

| ID | Publisher | Published | Retrieved | Availability | Page hash (SHA-256 of bytes received) |
| --- | --- | --- | --- | --- | --- |
| S-PUNCH-2025-06 | Punch Newspapers | 2025-06-23 | 2026-09-19 | available | `7605871bbe264a9ded4214b726801b70c9a30a899e14ece011f7473471d28794` |
| S-NATION-2025-01 | The Nation Newspaper | 2025-01-24 | 2026-09-19 | available | `950158e3cc040b41091a0b0d3cf93e9089490ded61727fe41d05c71fb2abc116` |
| S-ABUJATIMES-2026-07 | Abuja Times | 2026-07-15 | 2026-09-19 | available | `0ad70e5a3ddfa4950d1477bd76d4a17fc7f2c6ddabd29d93c3bc7b48da5761e9` |
| S-FCTUBEB-HOME | FCT Universal Basic Education Board (per the page; not independently confirmed) | unknown | 2026-09-19 | access_restricted | none (not retrieved) |
| S-HOSPITALBOOK-BWARI | The Hospital Book | unknown | 2026-09-19 | access_restricted | none (not retrieved) |

Each source's URL, retrieval method and reuse constraints:

- **S-PUNCH-2025-06** https://punchng.com/fg-constructed-150km-fct-satellite-towns-roads-in-one-year-wike/
  - Retrieval: http_200_full_page
  - Reuse: Copyrighted news article. Only short cited excerpts are kept; no licence terms were checked.
- **S-NATION-2025-01** https://thenationonlineng.net/over-n100bn-spent-on-bwari-road-projects-education-security-wike/
  - Retrieval: http_200_full_page
  - Reuse: Copyrighted news article. Only short cited excerpts are kept; no licence terms were checked.
- **S-ABUJATIMES-2026-07** https://abujatimes.com.ng/tinubu-commissions-water-supply-network-project-in-bwari/
  - Retrieval: http_200_full_page
  - Reuse: Copyrighted news article. Only short cited excerpts are kept; no licence terms were checked.
- **S-FCTUBEB-HOME** https://fctubeb.gov.ng/
  - Retrieval: direct_request_blocked_http_403_firewall; homepage read once through a summarising fetch tool (no raw bytes)
  - Reuse: Not checked. The register does not bypass the access block.
- **S-HOSPITALBOOK-BWARI** https://thehospitalbook.com/bwari-town-primary-health-center/
  - Retrieval: blocked_http_403_challenge_page
  - Reuse: Not checked; a commercial directory. The register does not bypass the access block.

## AMAC-01: Saburi I and II Access Road

- **Locality:** AMAC  
- **Category:** roads_public_works  
- **Proposed public status:** completed (A source reports the minister saying the road was completed and inaugurated; one media source only, so a reviewer must confirm.)  
- **Last checked:** 2026-09-19

### AMAC-01-F1

- **Statement:** Punch reports that the FCT minister described a 5km access road to Saburi I and II in Abuja Municipal Area Council as one of a list of roads completed and inaugurated.
- **Evidence:** exact_passage_verified; proposed verification state `awaiting_verification`; seed eligibility `eligible_as_cited_draft`
- **Note:** One independent media source, reporting the minister's statement.
- **Source:** S-PUNCH-2025-06
  - Exact passage: "I want to inform you that these roads have all been completed and inaugurated." (`0db033efd9d96b6e...`)
  - Exact passage: "Others are the 5km access road to Saburi I and II in Abuja Municipal Area Council and another 5-kilometre road in Abaji Area Council." (`8e28a3f42056fd78...`)

**Unresolved gaps**

- The road's budget or contract value is not stated in the source.
- The user-supplied phrase 'emergency satellite town interventions' does not appear in the fetched passages and is not used.

**[FICTIONAL REPORT FIXTURE]** *[DEMO ONLY]* A community submission claims that heavy rains have washed away a section of the road shoulder near Saburi II.
*Maintainer decision needed:* The wording refers to a real place or facility; decide whether to make it generic before any use.

## AMAC-02: Karshi Model Smart School

- **Locality:** AMAC  
- **Category:** education  
- **Proposed public status:** unknown (No delivery status was verified.)  
- **Last checked:** 2026-09-19

### AMAC-02-F1

- **Statement:** A headline on the FCT UBEB website, dated 12 March 2026, says its chairman commended progress at Karshi Model Smart School.
- **Evidence:** not_verified; proposed verification state `awaiting_verification`; seed eligibility `not_eligible`
- **Note:** Only the headline 'FCT UBEB Chairman commends progress at Karshi Model Smart School' with the date '12th March, 2026' was seen, and only through a summarising fetch tool. The longer passage came with the submitted draft and was not seen. Direct access returns HTTP 403.
- **Source:** S-FCTUBEB-HOME
  - Claimed but **not verified**: "The Acting Executive Chairman of the FCT Universal Basic Education Board (FCT-UBEB), Lady Florence Wenegieme, has reaffirmed the Board's commitment to strengthening innovative learning environments ... at Karshi Model Smart School."

**Unresolved gaps**

- No enrollment or launch date was seen.
- The exact article text could not be retrieved.

**[FICTIONAL REPORT FIXTURE]** *[DEMO ONLY]* An anonymous report indicates that digital learning equipment has been delivered but remains uninstalled in the main hall.
*Maintainer decision needed:* The wording refers to a real place or facility; decide whether to make it generic before any use.

## AMAC-03: Junior Secondary School, Lokogoma: toilets and desks

- **Locality:** AMAC  
- **Category:** water_sanitation  
- **Proposed public status:** unknown (No delivery status was verified.)  
- **Last checked:** 2026-09-19

### AMAC-03-F1

- **Statement:** The submitted draft says a Rotary club renovated and built 10 toilets and donated 120 desks at Junior Secondary School, Lokogoma.
- **Evidence:** not_verified; proposed verification state `awaiting_verification`; seed eligibility `not_eligible`
- **Note:** The passage was searched for on the FCT UBEB homepage through a summarising fetch tool and was not found there; direct access returns HTTP 403. A different page of the site may carry it.
- **Source:** S-FCTUBEB-HOME
  - Claimed but **not verified**: "Rotary Club of Abuja Sapphire Renovates, Builds 10 Toilets and Donates 120 Desks to Junior Secondary School, Lokogoma."

**Unresolved gaps**

- The source page for this claim has not been located.
- Water supply for the toilets is not stated in anything seen.

**[FICTIONAL REPORT FIXTURE]** *[DEMO ONLY]* A submission claims that despite the new toilets, the school's primary borehole pump is currently dysfunctional.
*Maintainer decision needed:* The wording refers to a real place or facility; decide whether to make it generic before any use.

## BWARI-01: Bwari Township Water Supply Network

- **Locality:** Bwari  
- **Category:** water_sanitation  
- **Proposed public status:** unknown (The source says the network was commissioned. Commissioning is not recorded as completion, so no completion is claimed.)  
- **Last checked:** 2026-09-19

### BWARI-01-F1

- **Statement:** Abuja Times reports that the President commissioned the 198-kilometre Bwari Township Water Supply Network Project in the FCT (article dated 15 July 2026).
- **Evidence:** exact_passage_verified; proposed verification state `awaiting_verification`; seed eligibility `eligible_as_cited_draft`
- **Note:** One independent media source.
- **Source:** S-ABUJATIMES-2026-07
  - Exact passage: "President Bola Ahmed Tinubu has commissioned the 198-kilometre Bwari Township Water Supply Network Project in the Federal Capital Territory (FCT)" (`db18729198bed705...`)

### BWARI-01-F2

- **Statement:** Abuja Times quotes the President as saying the network, constructed by China Geo-engineering Construction (CGC) Nigeria Limited, connects Bwari Township and surrounding communities to the Lower Usuma Dam.
- **Evidence:** exact_passage_verified; proposed verification state `awaiting_verification`; seed eligibility `eligible_as_cited_draft`
- **Note:** One independent media source.
- **Source:** S-ABUJATIMES-2026-07
  - Exact passage: "Tinubu explained that the newly commissioned water supply network, constructed by China Geo-engineering Construction (CGC) Nigeria Limited, connects Bwari Township and surrounding communities directly to the Lower Usuma Dam, the FCT’s primary source of treated water." (`48c9542240743b44...`)

**Unresolved gaps**

- The contract cost is not stated in the passages used.
- The submitted draft's phrase 'to improve access to clean water' is not in the source; the article says the President described it as a step towards improving residents' quality of life.

**[FICTIONAL REPORT FIXTURE]** *[DEMO ONLY]* Residents report that while main pipes are laid, lateral connections to individual streets in Ushafa are incomplete.
*Maintainer decision needed:* The wording refers to a real place or facility; decide whether to make it generic before any use.

## BWARI-02: Gaba-Tokulo Road

- **Locality:** Bwari  
- **Category:** roads_public_works  
- **Proposed public status:** completed (Two publishers report the road as completed and commissioned; both report the minister's statements.)  
- **Last checked:** 2026-09-19

### BWARI-02-F1

- **Statement:** Punch reports the minister listing a 7.2 km Gaba and Tokulo Road in Bwari Area Council among roads completed and inaugurated.
- **Evidence:** exact_passage_verified; proposed verification state `awaiting_verification`; seed eligibility `eligible_as_cited_draft`
- **Note:** One media source for the length. The 7.2 km figure is in this article, not in The Nation's.
- **Source:** S-PUNCH-2025-06
  - Exact passage: "I want to inform you that these roads have all been completed and inaugurated." (`0db033efd9d96b6e...`)
  - Exact passage: "He identified the roads as the 9km Paikon Kore to Ibwa Road in Gwagwalada Area Council, and 7.2 km Gaba and Tokulo Road in Bwari Area Council." (`341057fa03a7403a...`)

### BWARI-02-F2

- **Statement:** The Nation quotes the minister as saying the Gaba-Tokulo road project alone cost the government no less than N7 billion.
- **Evidence:** exact_passage_verified; proposed verification state `awaiting_verification`; seed eligibility `eligible_as_cited_draft`
- **Note:** A quoted figure of cost to the government; it is not a contract value.
- **Source:** S-NATION-2025-01
  - Exact passage: "“This Gaba-Tokulo road project alone cost the government no less than N7 billion. Since we flagged it off in January 2024, we ensured prompt payments, which allowed for timely completion without delays or abandoned contracts,” Wike stated." (`6febd8fa17c21ef2...`)

### BWARI-02-F3

- **Statement:** The Nation and Punch each report that the Gaba-Tokulo road in Bwari was commissioned or completed and inaugurated.
- **Evidence:** exact_passage_verified; proposed verification state `corroborated`; seed eligibility `eligible_as_cited_draft`
- **Note:** Two publishers, but both report the same minister; whether they are materially independent needs reviewer judgement.
- **Source:** S-NATION-2025-01
  - Exact passage: "Speaking during the commissioning of the Gaba-Tokulo road project in Bwari, Wike emphasised the administration’s commitment to delivering tangible development to every area council." (`f44a2c5324b0454e...`)
- **Source:** S-PUNCH-2025-06
  - Exact passage: "I want to inform you that these roads have all been completed and inaugurated." (`0db033efd9d96b6e...`)
  - Exact passage: "He identified the roads as the 9km Paikon Kore to Ibwa Road in Gwagwalada Area Council, and 7.2 km Gaba and Tokulo Road in Bwari Area Council." (`341057fa03a7403a...`)

### BWARI-02-F4

- **Statement:** The Nation reports that the contractor was directed to provide streetlights on the road beyond the initial contract scope.
- **Evidence:** exact_passage_verified; proposed verification state `awaiting_verification`; seed eligibility `eligible_as_cited_draft`
- **Note:** A directive, not a report that streetlights exist.
- **Source:** S-NATION-2025-01
  - Exact passage: "He also commended Setraco, the construction company, for delivering a high-quality road project, adding that the contractor has been directed to also provide streetlights on the road, beyond the initial scope of the contract." (`269234dee9ad7603...`)

**Unresolved gaps**

- No date is given for the streetlights.
- The article also mentions a plan to extend the road to Kawu; no timeline is stated.
- The submitted draft's 'contract cost of N7 billion' is worded here as the quoted cost to the government.

**[FICTIONAL REPORT FIXTURE]** *[DEMO ONLY]* A reviewer notes a submission claiming the promised streetlights along the road have not been installed.
*Maintainer decision needed:* The wording refers to a real place or facility; decide whether to make it generic before any use.

## BWARI-03: Bwari Town Primary Health Center, Kuduru

- **Locality:** Bwari  
- **Category:** health  
- **Proposed public status:** unknown (No delivery status was verified.)  
- **Last checked:** 2026-09-19

### BWARI-03-F1

- **Statement:** The submitted draft says a public Primary Health Care Centre is listed in Kuduru, Bwari, with facility code 37/02/1/1/1/0005, medical, paediatric and antenatal services, and 8 beds.
- **Evidence:** not_verified; proposed verification state `awaiting_verification`; seed eligibility `not_eligible`
- **Note:** The page returned an HTTP 403 challenge and was not read. The bed count and the services were not in the submitted passage at all.
- **Source:** S-HOSPITALBOOK-BWARI
  - Claimed but **not verified**: "The Bwari Town Primary Health Center is a Public hospital, located at Kuduru, Bwari Local Government, FCT State. ... with facility code 37/02/1/1/1/0005 and registered as Primary Health Care Centre."

**Unresolved gaps**

- The listing could not be retrieved.
- Staffing and drug stock are not in any source seen.
- A government facility register would be a stronger source than a commercial directory.

**[FICTIONAL REPORT FIXTURE]** *[DEMO ONLY]* A submitted report states the facility is chronically understaffed on weekends, leaving only one community health worker on duty.
*Maintainer decision needed:* The wording refers to a real place or facility; decide whether to make it generic before any use.

## Escalation guidance (not verified)

None of these has a cited source, verification date, or instructions, so none can be seeded (BE-042). No contact detail is recorded.

| Organisation | Purpose stated in the submitted draft | Status |
| --- | --- | --- |
| Tracka / BudgIT | independent civic monitoring and project tracking | unverified_no_source |
| Independent Corrupt Practices and Other Related Offences Commission (ICPC) | suspected procurement fraud or contractor misconduct | unverified_no_source |
| FCT Public Complaints Commission | administrative delays or service failures at Area Council level | unverified_no_source |
| Satellite Towns Development Department (STDD), FCTA | infrastructure deficits in Bwari and AMAC satellite towns | unverified_no_source |

## Locale text and translation labels

BWARI-01 summary. No fluent reviewer is recorded for any of these, so every one is `machine_assisted`.

- **en** (`machine_assisted`): The 198-kilometre water supply network connecting Bwari Township to the Lower Usuma Dam was commissioned.
  - Submitted as reviewed, but no reviewer or date is recorded, so it is labelled machine_assisted. The clause 'to improve access to clean water' was removed because the source does not say it.
- **ha** (`machine_assisted`): An ƙaddamar da aikin rarraba ruwa mai tsawon kilomita 198 da ke haɗa garin Bwari da madatsar ruwa ta Lower Usuma.
  - Submitted text with the unsupported purpose clause removed. Not reviewed by a fluent speaker.
- **ig** (`machine_assisted`): E mepere netwọkụ mmiri dị kilomita 198 nke jikọtara obodo Bwari na Lower Usuma Dam.
  - Submitted text with the unsupported purpose clause removed. Not reviewed by a fluent speaker.
- **yo** (`machine_assisted`): Wọ́n ti ṣe ifilọlẹ iṣẹ́ omi to gùn to ibusọ 198 (198-kilometre) to so ìlú Bwari pọ̀ mọ́ idido omi Lower Usuma (Lower Usuma Dam).
  - Submitted text with the unsupported purpose clause removed. Not reviewed by a fluent speaker.
