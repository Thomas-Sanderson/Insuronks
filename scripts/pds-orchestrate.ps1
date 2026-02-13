param(
  [Parameter(Mandatory = $true)]
  [string]$Task,
  [string[]]$Roles = @('researcher','worker','reviewer'),
  [string]$RunId = (Get-Date -Format 'yyyyMMdd-HHmmss'),
  [string]$Model = '',
  [switch]$NoAutoApply,
  [switch]$OpenWindowsTerminal,
  [switch]$Sequential,
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

function Require-Command([string]$Name) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Required command not found in PATH: $Name"
  }
}

function Get-RoleTemplatePath([string]$Root, [string]$Role) {
  return Join-Path $Root ".agent/roles/$Role.md"
}

function Build-Prompt(
  [string]$Role,
  [string]$TaskText,
  [string]$RunRoot,
  [string]$RoleOutputPath,
  [string]$RoleTemplate
) {
@"
$RoleTemplate

# Shared Task
$TaskText

# Constraints
- Work inside the current workspace only.
- Keep output concise and actionable.

# Output Contract
Write your final answer for this role. It will be saved to:
$RoleOutputPath

# Coordination Context
Run folder:
$RunRoot
"@
}

Require-Command 'codex'
$workspace = (Get-Location).Path
$runRoot = Join-Path $workspace ".agent/runs/$RunId"
New-Item -ItemType Directory -Path $runRoot -Force | Out-Null
Set-Content -Path (Join-Path $runRoot 'task.md') -Value $Task -Encoding UTF8

$processes = @()

foreach ($role in $Roles) {
  $roleName = $role.Trim().ToLowerInvariant()
  if ([string]::IsNullOrWhiteSpace($roleName)) { continue }

  $roleDir = Join-Path $runRoot $roleName
  New-Item -ItemType Directory -Path $roleDir -Force | Out-Null

  $templatePath = Get-RoleTemplatePath -Root $workspace -Role $roleName
  if (-not (Test-Path $templatePath)) {
    throw "Role template missing: $templatePath"
  }

  $roleTemplate = Get-Content -Path $templatePath -Raw -Encoding UTF8
  $outputPath = Join-Path $roleDir 'output.md'
  $promptPath = Join-Path $roleDir 'prompt.md'
  $statusPath = Join-Path $roleDir 'status.txt'
  $stdoutPath = Join-Path $roleDir 'stdout.log'
  $stderrPath = Join-Path $roleDir 'stderr.log'

  Set-Content -Path $statusPath -Value 'queued' -Encoding UTF8

  $prompt = Build-Prompt -Role $roleName -TaskText $Task -RunRoot $runRoot -RoleOutputPath $outputPath -RoleTemplate $roleTemplate
  Set-Content -Path $promptPath -Value $prompt -Encoding UTF8

  $args = @('exec', '--skip-git-repo-check', '--output-last-message', $outputPath)
  if (-not $NoAutoApply) {
    $args += '--full-auto'
  }
  if (-not [string]::IsNullOrWhiteSpace($Model)) {
    $args += @('--model', $Model)
  }
  $args += $prompt

  if ($OpenWindowsTerminal) {
    Require-Command 'wt'
    $quoted = @()
    foreach ($a in $args) {
      if ($a -match '\s') {
        $quoted += '"' + $a.Replace('"','\\"') + '"'
      } else {
        $quoted += $a
      }
    }
    $argLine = ($quoted -join ' ')
    $cmd = "Set-Location '$workspace'; codex $argLine; Write-Host ''; Write-Host 'Role complete: $roleName';"
    Start-Process -FilePath 'wt' -ArgumentList @('new-tab','--title',"agent-$roleName",'powershell','-NoExit','-ExecutionPolicy','Bypass','-Command',$cmd) | Out-Null
    Set-Content -Path $statusPath -Value 'running (terminal)' -Encoding UTF8
    continue
  }

  if ($DryRun) {
    Set-Content -Path $statusPath -Value 'dry-run (prepared only)' -Encoding UTF8
    continue
  }

  Set-Content -Path $statusPath -Value 'running' -Encoding UTF8
  if ($Sequential) {
    $proc = Start-Process -FilePath 'codex' -ArgumentList $args -WorkingDirectory $workspace -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath -PassThru -Wait
    if ($proc.ExitCode -eq 0) {
      Set-Content -Path $statusPath -Value 'completed' -Encoding UTF8
    } else {
      Set-Content -Path $statusPath -Value "failed ($($proc.ExitCode))" -Encoding UTF8
    }
  } else {
    $proc = Start-Process -FilePath 'codex' -ArgumentList $args -WorkingDirectory $workspace -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath -PassThru
    $processes += [pscustomobject]@{ Role = $roleName; Process = $proc; StatusPath = $statusPath }
  }
}

if (-not $OpenWindowsTerminal -and -not $DryRun -and -not $Sequential -and $processes.Count -gt 0) {
  foreach ($p in $processes) {
    Wait-Process -Id $p.Process.Id
    if ($p.Process.ExitCode -eq 0) {
      Set-Content -Path $p.StatusPath -Value 'completed' -Encoding UTF8
    } else {
      Set-Content -Path $p.StatusPath -Value "failed ($($p.Process.ExitCode))" -Encoding UTF8
    }
  }
}

Write-Host "Run completed: $runRoot"
Get-ChildItem -Path $runRoot -Recurse -File |
  Where-Object { $_.Name -in @('status.txt','output.md','stderr.log') } |
  Select-Object FullName, Length
