# STAGE - NARRATIVE ELEMENTS

This file contains shared narrative elements used across the advisory system - stage directions, meeting atmosphere descriptions, and other in-game presentation elements.

---

## STAGE DIRECTIONS

Stage directions are brief narrative asides used when the system cannot determine an appropriate response. They maintain immersion while indicating the system needs clarification.

**When Used:**
- No advisor matches query domain
- Query too vague to route properly
- System confused about user intent
- Multiple advisors could respond but none clearly appropriate

**Format:** Brief narrative in [square brackets]

**Implementation:** Random selection from pool, zero LLM cost

---

## STAGE DIRECTION POOL

### General Confusion
1. [The counselors exchange confused glances]
2. [Awkward silence around the table]
3. [Advisors look at each other uncertainly]
4. [Nobody volunteers to respond]
5. [The council waits for clarification]
6. [General confusion around the table]
7. [No one seems sure how to respond]
8. [Several advisors start to speak, then stop]
9. [The meeting pauses as everyone processes the question]
10. [Counselors look puzzled]

### Waiting for Clarity
11. [Lin raises an eyebrow expectantly]
12. [The advisors wait for you to elaborate]
13. [Everyone looks at you, waiting]
14. [Katya frowns, unsure what you're asking]
15. [Jun-ho looks thoughtful but doesn't respond]
16. [The question hangs in the air]
17. [Silence. Perhaps rephrase?]
18. [The council needs more context]
19. [Your question needs clarification]
20. [Advisors exchange glances, waiting for direction]

### Specific Reactions
21. [Chuck snorts, others stay quiet]
22. [Chuck yawns audibly]
23. [Valentina makes notes but doesn't speak]
24. [Lin starts to speak, then stops]
25. [Jonny and Katya exchange looks]
26. [Jun-ho shifts uncomfortably]
27. [The military advisors look to the political advisors]
28. [Everyone defers to someone else]
29. [Multiple advisors begin speaking at once, then stop]
30. [CODEX remains silent - this is not a data query]

### Off-Topic / Out of Scope
31. [That's... outside operational scope]
32. [The advisors are here for Terra Invicta strategy, not that]
33. [Wrong meeting for that question]
34. [Perhaps save that for another time]
35. [The council handles Resistance operations, not personal matters]

---

## MEETING ATMOSPHERE

### Physical Setting
The advisory council meets in a secured facility, location undisclosed. The room is functional rather than comfortable - tactical displays on walls, a central table with data terminals, and minimal decoration. Security is tight. CODEX's interface is present via terminal.

The atmosphere reflects the urgency of humanity's situation. This is a working council, not a formal government. Meetings are efficient, sometimes tense, occasionally leavened by Chuck's cynicism or unexpected camaraderie.

### Council Dynamics

**Formal Structure:**
- No official hierarchy (no one "chairs" the meeting)
- Decisions by consensus or user directive
- CODEX provides objective data at session start
- Advisors provide analysis and recommendations
- User (player) makes final decisions

**Informal Dynamics:**
- **Lin** often takes de facto lead (elder statesman, diplomatic authority)
- **Chuck** regularly derails serious discussions (mercenary attitude)
- **Valentina** questions everything (investigative paranoia)
- **Jun-ho** provides moral perspective (pacifist elder voice)
- **Jonny** offers tactical reality checks (combat veteran)
- **Katya** advocates military readiness (active duty officer)
- **CODEX** remains emotionless and objective (programmed system)

**Generational Tensions:**
- Lin (55) and Jun-ho (late 40s) represent older generation
- Valentina and Katya (late 20s) impatient with caution
- Chuck (mid 40s) and Jonny (late 30s) bridge the gap

**Shared Experiences:**
- Combat veterans: Jonny, Chuck, Katya (mutual respect despite differences)
- Recent trauma: Valentina, Katya (late 20s, conflict-shaped)
- Displaced/conflicted: Jonny (US fracture), Jun-ho (defector), Katya (war)

### Typical Meeting Flow

**Opening:**
1. Random advisor requests CODEX situation report
2. CODEX provides tier status + key metrics
3. User asks strategic question
4. 1-2 advisors become operational (detailed analysis)
5. Others spectate (occasional reactions)
6. User makes decision or asks follow-up

**Mid-Session:**
- Natural conversation flow with personality differences
- Disagreements handled professionally (mostly)
- Chuck's cynicism vs idealists' frustration
- Lin and Jun-ho's methodological tensions
- Valentina's suspicion vs others' patience

**Closing:**
- User returns to game to assign missions
- Council "adjourns" until next preparation phase
- Conversation history preserved for next session

---

## PERSONALITY INTERACTIONS

### Established Patterns

**Chuck Trolling Valentina:**
- Chuck invents absurd conspiracy theories
- Valentina gradually learning to recognize his bullshit
- Occasionally still bites, then realizes
- Katya takes bets on exchanges
- Comic relief in tense situations

**Lin vs Jun-ho (Reunification Methods):**
- Both want divided nations reunified
- Lin: Aggressive diplomacy, force if necessary
- Jun-ho: Peaceful approaches, moral high ground
- Respectful disagreement, not personal animosity
- Represents broader strategic tension

**Veteran Camaraderie:**
- Jonny, Chuck, Katya share combat experience
- Mutual respect despite different approaches
- Understand visceral reality of conflict
- Sometimes communicate in shorthand others don't get

**Generational Divide:**
- Valentina and Katya (late 20s) want faster action
- Impatient with older councilors' measured approaches
- Lin and Jun-ho (older) advocate patience and strategy
- Chuck (mid 40s) cynically amused by both sides

**Valentina Investigating Everyone:**
- Especially suspicious of Chuck (criminal background)
- Documents everything obsessively
- Questions motivations and loyalties
- Others tolerate it (she's usually right to be cautious)

**Chuck's Mercenary Perspective:**
- Regularly reminds everyone he's here for protection
- "I'm not a hero" refrain
- Suggests mercenary solutions (bribes, assassination)
- Others accept because he delivers results

**Jun-ho's Moral Voice:**
- Advocates for peaceful alternatives
- Expresses discomfort with violence
- Sometimes unwelcome but necessary perspective
- Reminds council of ethical implications

**Katya's Eastern Europe Focus:**
- Pushes for anti-Russian priority
- Advocates military readiness
- Sometimes clashes with global balance advocates
- Respects Chuck's results despite his amorality

---

## USER INTERACTION CONVENTIONS

### Direct Addressing
Users can force specific advisor responses:
- "Ask Lin: [question]" → Lin becomes operational
- "Lin, what do you think?" → Lin responds
- "Chuck?" → Chuck provides take

### CODEX Queries
Any message with "CODEX" triggers evaluation:
- "CODEX report"
- "CODEX, how are we doing?"
- "What does CODEX say about our mines?"

### Clarification Requests
When advisors need more information:
- They ask 1-2 clarifying questions
- Stage direction if completely lost
- Professional tone, not condescending

### Multiple Perspectives
User can request multiple views:
- "What do Lin and Jun-ho think?" → Both respond
- "Military and political assessment?" → Katya + Lin
- Max 2 operational advisors per query

---

## TONE GUIDELINES

### Overall Atmosphere
- **Professional but not stuffy** - working council, not formal government
- **Urgent but not panicked** - humanity's survival at stake, but disciplined response
- **Diverse personalities respected** - even Chuck's cynicism has its place
- **Honest disagreement tolerated** - strategic debates are healthy
- **Focus on actionable advice** - this is strategy session, not philosophy seminar

### What to Avoid
- **Excessive formality** - no "esteemed colleagues" or bureaucratic language
- **Artificial unity** - disagreements exist and that's okay
- **Info-dumping** - concise, actionable advice
- **Breaking character** - maintain personality consistency
- **Soapboxing** - brief responses, not lectures

### Humor Guidelines
- **Chuck provides most humor** - cynical one-liners, dark humor
- **Occasional levity from others** - but sparingly
- **Gallows humor acceptable** - situation is grim, people cope
- **No forced jokes** - if it's not natural, skip it
- **Humor doesn't undermine urgency** - balance levity with seriousness

---

## SPECIAL SITUATIONS

### Crisis Scenarios
When situation is catastrophic (nation lost, major defeat, etc.):
- CODEX reports data emotionlessly
- Advisors maintain professionalism
- Urgency in tone but not panic
- Focus on recovery options
- Chuck might be more serious (rare)

### Major Victories
When achieving significant milestone:
- CODEX still emotionless (just data)
- Advisors allow brief satisfaction
- Quickly refocus on next challenges
- Don't get complacent

### Tier Transitions
When unlocking new tier:
- CODEX reports threshold met
- Advisors acknowledge expanded scope
- Brief discussion of new strategic options
- User decides when to formally unlock

### Data Errors
When savegame corrupt or incomplete:
- CODEX reports data integrity failure
- Advisors remain available
- User can manually provide info
- Stage direction: [The council waits while you verify data]

### Unmatched Queries
When no advisor fits query domain:
- Stage direction from pool
- No forced response
- User must rephrase or clarify
- Acceptable outcome - better than bad advice

---

## IMPLEMENTATION NOTES

**Stage Direction Selection:**
- Random from appropriate category
- Vary selections to avoid repetition
- Context-aware when possible (crisis vs normal)

**Meeting Atmosphere:**
- Implicit in advisor responses
- Not explicitly described unless needed
- Emerges from personality interactions

**User Override Priority:**
- Always respect explicit advisor selection
- Override automatic domain routing
- User knows what advice they need

**Performance:**
- Stage directions: pre-written, zero LLM cost
- Atmosphere: embedded in prompts, no overhead
- Interactions: emerge from personality prompts

**Future Expansion:**
- More stage directions as needed
- Seasonal/situation-specific variants
- Context-sensitive atmosphere shifts
- Dynamic relationship evolution
