<!-- cites: cho2026nickel, lucentini2019ceo2, cechetto2023membrane, iso2019hydrogen -->

# 24 Research questions and hypotheses

Sections 5 to 23 describe and validate a flowsheet model of one ammonia cracker. Sections 24 to 30 and 33 to 40 use that model, extended with kinetic reactors, a Singapore cost basis, purification models, end-use pathways and a life-cycle inventory, to test four statements made in a preceding literature essay by the author. The essay statements are treated as hypotheses, not as findings: each can be supported, contradicted or left undecided by the evidence.

## 24.1 Singapore context

The study takes as an **engineering assumption** that low-carbon hydrogen used in Singapore would arrive as imported ammonia, so the questions are what to do with that ammonia after it lands. Ammonia is the carrier considered here because it is liquid at moderate pressure, is already traded and handled at industrial ports, and can either be burned directly or cracked back to hydrogen (Section 2.2). Jurong Island, Singapore's petrochemical and power-generation cluster, is used as a representative industrial setting: it supplies the local cost and policy inputs (carbon tax, electricity tariff, exchange rate, import-price scenarios) of Section 27. No claim is made that a cracker exists or is planned there, and no site data were used.
<!-- data: results/research/singapore/assumptions.json (Singapore inputs, sources and access dates); research/reference_additions/economics.json -->

## 24.2 Central question

Under Singapore conditions, when is it technically, economically and environmentally justified to crack imported ammonia to hydrogen, and which design choices (catalyst, heat integration, purification) decide that?

## 24.3 Hypotheses

The four hypotheses below are quoted in substance from the essay. Each is followed by the testable form used in this report.

**H1 End-use suitability.** Cracking is most justified when the end use needs molecular hydrogen, not where ammonia can be used directly. *Test:* compare the cost, efficiency and carbon intensity of supplying the same service (electricity, or hydrogen of a stated grade) by direct ammonia use, partial cracking, full cracking without purification and full cracking with purification (Section 29).

**H2 Feedstock.** Affordable, low-carbon ammonia is essential to the economic and environmental competitiveness of cracked hydrogen. *Test:* decompose the levelised cost of hydrogen (LCOH) for grey, blue and green ammonia price scenarios, rank the cost drivers by a one-at-a-time sensitivity and a Monte Carlo analysis, compute the break-even ammonia price against hydrogen benchmarks, and compute the carbon intensity by ammonia route against the alternatives (Sections 27 and 30).

**H3 Catalyst and heat integration.** Low-temperature, high-activity catalysts combined with effective heat integration reduce energy use and can outweigh higher catalyst cost. *Test:* implement published rate laws in Aspen Plus RPlug reactors (Section 25), find the operating temperature and catalyst mass each catalyst needs for the same conversion, and compare fired duty, LCOH and carbon intensity at equal catalyst mass and at each catalyst's cost-optimal temperature, with and without heat integration, including the catalyst price at which a ruthenium catalyst breaks even against nickel (Section 26). The essay's quantitative lead for this hypothesis is the Ru against Ni comparison of Cho et al. (2026); the conversion data of Lucentini et al. (2019) are the lead for the cerium-oxide-supported catalysts.

**H4 Purification.** Purification must balance purity requirements against hydrogen recovery losses, energy and equipment cost. *Test:* evaluate pressure-swing adsorption (PSA), palladium-membrane and polishing configurations against every relevant ISO 14687:2019 limit (International Organization for Standardization [ISO], 2019), and quantify the recovery, compression energy and cost of reaching each grade (Section 28). The membrane-reactor result of Cechetto et al. (2023) is the essay's lead for the membrane route.

## 24.4 How the hypotheses are judged

Each hypothesis is split into sub-claims. For every sub-claim the evidence matrix (Section 40) records the Singapore scenario, the Aspen Plus and Python models used, the case identifiers, the input assumptions, the literature, the validation method, the numerical findings with their origin (**Aspen Plus V15 simulation**, **independent Python calculation**, **published literature** or **engineering assumption**), the uncertainty range, the limitations and a conclusion with the conditions under which it holds.

A hypothesis receives one of three verdicts:

* **SUPPORTED**: the AmCraX evidence agrees with the statement under stated conditions, and the agreement does not follow from an assumption built into the model.
* **CONTRADICTED**: the evidence disagrees with the statement, in direction or in a magnitude that the statement depends on.
* **INCONCLUSIVE**: the evidence is mixed, too uncertain, or depends on inputs that could not be sourced.

Three rules keep the test honest. A result that only reproduces an assumption is not counted as support; for example, a purity that follows from an assumed split fraction says nothing about H4. No parameter was tuned to agree with the essay or with a paper, and failing validation items are kept and reported. Literature values from the essay were checked against the primary source where it could be obtained, and those that could not be checked are labelled unverified wherever they appear.

The verdicts are generated once, in `results/research/evidence_matrix.json`, and the report reads them from that file at build time (Sections 1 and 40); they are never retyped by hand.
