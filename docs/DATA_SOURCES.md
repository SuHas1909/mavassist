# Directory data sources (FR-02, risk R-03)

All 50 directory records are defined in `backend/app/services_seed.json`. Details were read from public uta.edu pages on **October 20, 2026**. A record is marked `verified` only when every displayed field came from the cited page; where a page did not publish a field, the record says so (for example "See the official page for current hours") instead of guessing.

| Status | Count | Records |
|---|---|---|
| Verified | 48 | All others |
| Needs review | 2 | Student Money Management (no dedicated public page found; routed to Financial Aid), Library Technology Lending (equipment page not publicly visible) |

## Main pages used

| Office / topic | Source |
|---|---|
| Student Accounts | https://www.uta.edu/business-affairs/student-accounts/ |
| Financial Aid, Scholarships, Veteran benefits | https://www.uta.edu/fao/contact/ and the FAO VA contact sheet |
| Emergency Assistance Fund | https://www.uta.edu/student-affairs/dos/advocacy/emergency-assistance |
| University Advising Center | https://www.uta.edu/student-success/advising-redesign/contact-us |
| Academic Success Center, Writing Center, Math Clinic, TRIO, UAC phone | UTA "No Limits" quick reference (uta.pressbooks.pub) and Division of Student Success pages |
| Registrar, transcripts, graduation | https://uta.edu/administration/registrar/about/contact |
| Undergraduate Research | https://www.uta.edu/research/opportunities/undergraduate-research |
| Graduate School | https://www.uta.edu/academics/schools-colleges/gradschool/students |
| UTA Libraries | https://libraries.uta.edu/hours-locations |
| Health Services | https://www.uta.edu/student-affairs/health-services/contact |
| CAPS / MAVS TALK | https://www.uta.edu/student-affairs/caps/contact |
| SAR Center | https://www.uta.edu/student-affairs/sarcenter |
| Maverick Pantry | https://uta.edu/student-affairs/health-and-wellness/maverick-pantry |
| Campus Recreation | https://www.uta.edu/student-affairs/campus-recreation |
| RVSP | https://www.uta.edu/student-affairs/rvsp |
| Dean of Students, CARE Team | https://www.uta.edu/student-affairs/dos/contact |
| OIE (ISSS, employment, study abroad) | https://uta.edu/student-affairs/oie/about-oie/contact-us |
| International health insurance | https://uta.edu/student-affairs/oie/isss/health-insurance |
| Orientation, Parent & Family | https://www.uta.edu/student-affairs/nstfp/new-student/transfer |
| English Language Institute | https://eli.uta.edu/contact-us |
| OIT Service Desk, software, labs | https://oit.uta.edu/ |
| Canvas support | https://uta.edu/administration/distance/canvas/technical-support |
| Housing | https://www.uta.edu/campus-ops/housing/contact |
| Dining | https://www.uta.edu/dining |
| Parking & Transportation | https://www.uta.edu/pats |
| Mav Express | https://www.uta.edu/campus-ops/mavexpress |
| Student Organizations | https://www.uta.edu/student-affairs/student-organizations/contact |
| Student Governance | https://www.uta.edu/student-affairs/student-governance/contact |
| Intercultural Student Engagement Center | https://www.uta.edu/student-affairs/intercultural-student-engagement-center/contact |
| Career Development Center | https://events.uta.edu/career_development_center_520 |
| Community Standards (conduct) | https://www.uta.edu/student-affairs/community-standards/contact |
| UTA Police | https://www.uta.edu/campus-ops/police/services/dispatch-services |
| Spring 2026 facility hours (Library, MAC, University Center) | The Shorthorn, "UTA facilities' spring 2026 hours of operation" |

## Known inconsistencies to resolve

* Health Services' contact page lists 605 S. West Street, while the CAPS page lists 605 W. 1st Street for psychiatry at Health Services. The record uses the Health Services page.
* The Housing contact page lists both 109 W. 2nd Street ("Come Visit Us") and the University Center main level for staff. The record uses the visitor address.
* Library, MAC and pantry hours were published for Spring 2026 and are labelled that way.

## Review process

Administrators can see "Needs source review" counts on the Manage resources page, filter to those records, and tick "I checked these details against the official source" when saving. The seed never overwrites a record an administrator has edited.
