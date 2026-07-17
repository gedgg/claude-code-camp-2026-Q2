## Preweek Technical Documentation
 
### Summary
 
Below "technical" documentation will be inevitably intertwined with personal reflections and educational goals. Fact is - I am nowhere at the level to talk about SDKs or compare technologies as per Andrew's Journaling video. Therefore the biggest goal of them all is to consume course material and learn as much as possible. This involves prerequisite catch-up, course material unpacking, following along where applicable and most importantly learning something new.
 
## Technical Goals
 
1. Catch up with prerequisites to be able to follow the course
2. Unpack and understand course material
3. Be able to partake in the course (follow along)
4. Deepen technical understanding of Claude code, agentic loops, coding harness etc (Learn)
5. Anything else - a bonus (unknown unknown) - I don't know what I don't know and I don't know what I will learn. Until I see the course material and try for myself.
### 1. Prerequisites
 
Albeit considering myself a tech-savvy professional (at least in my field) I don't use technologies like WSL2, Git, Docker on a day to day basis. Thus technical goal 1 - catch up and prepare for the course so I can follow without much interruption.
 
### 2. Course unpacking and 3. Following along
 
Learn to learn
 
### 4. Claude Code
Consume material and learn
 
## Technical Observations
 
### Prerequisites
 
Having read the prerequisites for the course I took action to address my own shortcomings where I saw them. I spent the entire day on Saturday before the course launch going through prerequisites (being on London time means I had a head start). I split the prerequisites into bite size chunks and addressed the ones with most impact:
1. WSL2 - Never worked with it, but did have a separate Ubuntu laptop (converted an old "potato" laptop to Ubuntu). WSL, however, was new. Read up documentation and managed to install without much trouble. At the end of the day - I learnt something new.
2. Containers - never touched Docker before. Installed Docker Desktop, installed Docker on WSL, configured both to work with each other. Read up on basic Docker usage, build, ran my hello world, read up on Docker Compose. When Andrew said "if you don't know how to install docker, go find out" - this did not apply to me as I was prepared and was able to follow along with no interruption. 
3. GITHUB - basic tool for a tech professional, and yet I don't have to work with it ever! I understand basic principles and can navigate it with cheat sheet in front of me, I am constantly trying to prevent myself from committing something that will automatically fail me :worried:
### 2. Course unpacking and 3. Following along
Learning to learn is an art in itself. Andrew (bless him) has a very distinctive teaching style that involves him doing "stuff" on the fly and, when facing an issue, figuring it out on video. This is great as it shows the possible issues that may occur and the frame of mind that it takes to solve them and the actual solution to the problem. On the opposing side it breaks the flow or continuum of the unknown subject that is being discussed and introduces loops and rabbit holes and unknown or yet uncovered material which in itself adds complexity.
 
### 4. Claude Code
 
#### MUD 
I had a bias against MUD - something I never fully understood. "Text based games?! Have you not tried 'Last of Us'?" However going deeper into the course the bias was cleared and I learnt to at least tolerate it (and went in deep with 02_agent_skills)
 
#### Claude code
 
When it came to implementing Claude code onto MUD - first attempt with plain agent 01_plain_agent was an obvious bust - having watched the video I felt there's nothing to gain from following this along and doing it myself. The solution simply did not work and I did not identify any material takeaways other than "this does not work".
 
Second attempt on 02_agent_skills went much more smoothly. Andrew had issues installing the skill-creator on his machine which I could not replicate. Installation of skill-creator went smoothly. Due to my learning style (watching first, then doing on my own from notes) I already knew that I have to implement basic logging logic to track actions.md, player.md and world.md. This resulted in a quite smoothly working agent as it kept logs of what it did before or what I asked it before. For example one of the first asks was "find something to eat and drink." The agent quickly found water, but could not figure out how to eat for free. This resulted in a secondary objective of gold search (the agent learnt that it needs gold to do basics like eating) [See actions.md Line 77](./week0_explore/explore_architecture/02_agent_skills/mud-logs/actions.md#L77)
 
When given a more complex task "Find Red Room" - contrary to Andrew I did not mention it was north from the temple - which resulted in the Agent going off searching the entire map, finding Sewer and getting lost. The agent was unable (or unwilling) to backtrack and only with my intervention did the agent find (was given the sequence) its way out. It did, however, collect gold where it could. [See actions.md Line 214](./week0_explore/explore_architecture/02_agent_skills/mud-logs/actions.md#L214) The agent also intuitively collected free items (including sword and shield [See actions.md Line 231](./week0_explore/explore_architecture/02_agent_skills/mud-logs/actions.md#L231)) even though no one told it to. 
 
Overall the agent was capable of playing the game, and took some intuitive leaps, i.e. trying combat or collecting items when not prompted, however it lacked robustness when executing poorly defined tasks (Find red room). The skill would benefit from a hierarchical action plan or strategy - i.e.: "eat when you can, drink when you can, collect items, store money, etc." Navigation is implemented poorly and .md is not fit for purpose. It explains why agent coun't not backtrack it's steps regardless them being recorded on .md file. Something like a graph database (Andrew mentioned that so I cannot pass it off as an original idea :) ) enabling routing algorithms - for example: the agent found out that different terrains use a different number of movement points [See world.md Line 250](./week0_explore/explore_architecture/02_agent_skills/mud-logs/world.md#L250) - you could record how many movement points it takes to traverse from node to node and use them as weights in a graph and apply Dijkstra's shortest path algorithm to find the quickest way to the desired destination. This only applies when sufficient map exploration is done.
 
## Technical Conclusion
 
### 1. Prerequisites
 
I spent the entire day on Saturday before the course launch going through prerequisites (being on London time means I had a head start). I figured out WSL2, Docker, read on AI and Agentic loops and had a crash course in Git and GitHub. This allowed me to follow the course with minimal technical interruptions.
 
### 2. Course unpacking and 3. Following along
 
Found my learning curve that works for me which reminds me of uni work back in 2009 - consume material beforehand and understand the objectives and possible pitfalls, take notes, before deep diving on my own. Learn from Andrew not only by following along but also from all the little things that happen in the course and try to implement straight away.
 
### 4. Claude code
 
1. 01_plain_agent failed to play the game
2. 02_agent_skill was able to play the game, took some intuitive leaps but lacked robustness when faced with advanced problems. Additional skill definition and different game data storage options may benefit the agent drastically.

## Key takeaway
 
1. Decision to make time to study prerequisites paid off
2. Agent implementation architecture matters - more granular definition gives better results. Correct tool selection is paramount as .md files lack structure and funcitonality and searchability.
3. MUD is not too bad