# Anti-Pattern: Script With Report

## What It Looks Like

A repo has a Python script, seeded input, and a generated report. The demo runs, but the user never gets a product surface, review loop, state, or workflow controls.

## Why It Fails

This may be useful infrastructure, but it rarely feels like a company. A buyer cannot see where they would live in the product or how it would become part of their recurring workflow.

## How To Detect It

- The main demo is one command that emits files.
- The only output is a static report.
- There is no operator-facing UI, workspace, dashboard, cockpit, CLI flow, or artifact viewer.
- Tests check file generation more than output usefulness.

## How To Fix It

Build a product surface around the job: input intake, generated artifact, review/edit state, comparison, export, and next action. Make `make receipt` produce something a buyer would actually use.
