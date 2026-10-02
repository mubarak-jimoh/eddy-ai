# EddyAI – Case Study

EddyAI is an AI-powered student support app I worked on as part of a team at Pilot Generative AI.

Staff enter a student's needs and the problem they are facing. EddyAI then generates a personalised support plan, structured with the PCAR framework.

> This repository is a case study. The code belongs to Pilot Generative AI, so it is not published here.

## The PCAR framework

Every support plan follows the same four steps, so staff get a consistent, structured analysis instead of free-form text.

| Step | What EddyAI produces |
| --- | --- |
| **Problem** | A clear statement of the difficulty the student is facing |
| **Cause** | The possible causes behind it |
| **Action** | Practical support that staff can put in place |
| **Result** | The intended outcome of that support |

## Features

- **Personalised support plans** generated from the student's needs and the problem described
- **Structured PCAR output**, so every plan is laid out the same way and is easy to act on
- **Secure login**, so only authorised staff can use the app
- **Saved reports**, so plans can be returned to later
- **Admin dashboard** where authorised staff review and manage saved reports

## How it works

1. A member of staff signs in.
2. They enter the student's needs and the problem.
3. The Flask app sends this to an AI model with instructions to answer in the PCAR structure.
4. The plan is shown to the user and saved as a report.
5. Authorised staff can review and manage saved reports from the admin dashboard.

## Tech

- Python and Flask
- Generative AI for producing the support plans
- User authentication and role-based access for the admin dashboard

## What I learned

- Building a web app with Flask as part of a team
- Getting structured, repeatable output from an AI model instead of free-form text
- Handling sensitive information responsibly: login, access control and limiting who can see saved reports
- Working to a real organisation's requirements instead of my own
