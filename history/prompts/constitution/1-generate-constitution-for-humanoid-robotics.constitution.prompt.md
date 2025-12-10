---
id: 1
title: Generate Constitution for Humanoid Robotics
stage: constitution
date: 2025-12-06
surface: agent
model: Gemini
feature: none
branch: main
user: unspecified
command: /sp.constitution
labels: ["constitution", "robotics", "ai", "ethics"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - .specify/memory/constitution.md
tests:
 - none
---

## Prompt

/sp.constitution Generate the Constitution for a Global Rulebook on Physical AI and Humanoid Robotics:
Create a legal framework for Physical AI and humanoid robotics, outlining key regulatory standards, ethical guidelines, and usage restrictions.
Key Sections:
1.	Regulatory Authority (AIRLA)
o	Establish the AI and Robotics Law Authority (AIRLA) to monitor AI and robotics organizations.
o	AIRLA approves the Articles of Association for each organization based on country-specific requirements.
2.	Vision
o	Build a world where robots enhance human well-being, productivity, and quality of life while ensuring ethical development.
3.	Ethical Principles
o	Robots must:
	Respect human rights and privacy.
	Avoid harm to humans and the environment.
	Be transparent, inclusive, and serve societal needs.
4.	Usage Limitations
o	Ban robots used for military or destructive purposes.
o	Restrict robots in games or applications that promote violence.
5.	Positive Applications
o	Focus on beneficial uses of robots, including:
	Healthcare, domestic help, education, and service industries.
o	Ensure robots support human labor and don’t replace jobs, promoting job creation.
6.	Age Restrictions
o	Real robots can only be operated by licensed individuals.
7.	Tech Stack
o	Documentation should be created using Docusaurus, prioritizing hands-on learning for beginners to intermediates.

## Response snapshot

I have successfully generated the project constitution based on your request. The new constitution is located at `.specify/memory/constitution.md`.

## Outcome

- ✅ Impact: Created the initial project constitution, establishing the core principles for the Humanoid Robotics project.
- 🧪 Tests: none
- 📁 Files: - .specify/memory/constitution.md
- 🔁 Next prompts: none
- 🧠 Reflection: The process of creating a constitution from a template and user input was successful. The consistency check of other project files was an important step.

## Evaluation notes (flywheel)

- Failure modes observed: `git rev-parse --abbrev-ref HEAD` failed, likely due to a new repository with no commits. Handled by using 'main' as a default.
- Graders run and results (PASS/FAIL): PASS
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): n/a
