param(
  [Parameter(Mandatory = $true)]
  [string]$Problem,
  [string]$Model = '',
  [switch]$DryRun,
  [switch]$Sequential
)

$ErrorActionPreference = 'Stop'
$task = @"
Swarm the ACA SBC parsing reliability problem and produce deterministic parser improvements.

Problem statement:
$Problem

Hard requirements:
1) Runtime parsing must be deterministic (no LLM calls in parsing path).
2) Propose and implement explicit extraction rules with precedence.
3) Add or update repeatable validation commands and acceptance checks for bulk runs.
4) Preserve compatibility with existing output columns.
5) Document residual failure classes and what data to capture for future rule additions.

Deliverables by role:
- researcher: extraction-rule map, failure taxonomy, prioritized plan
- worker: concrete code changes
- reviewer: severity-ranked findings and reliability sign-off criteria
"@

$args = @('-NoProfile','-ExecutionPolicy','Bypass','-File','.\\scripts\\pds-orchestrate.ps1','-Task',$task)
if (-not [string]::IsNullOrWhiteSpace($Model)) {
  $args += @('-Model',$Model)
}
if ($DryRun) {
  $args += '-DryRun'
}
if ($Sequential) {
  $args += '-Sequential'
}

& powershell @args
