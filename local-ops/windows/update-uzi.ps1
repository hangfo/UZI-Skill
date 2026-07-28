param(
    [ValidateSet("Audit", "ApplySkills")]
    [string]$Mode = "Audit"
)

$ErrorActionPreference = "Stop"

$UZI_ROOT = "D:\UZI-Skill"
$SKILL_ROOT = "$env:USERPROFILE\.agents\skills"
$OPS_ROOT = "$UZI_ROOT\local-ops"
$STATE_FILE = "$OPS_ROOT\windows\uzi-skill-update-state.json"
$BACKUP_ROOT = "$OPS_ROOT\backups\stock-skills"
$KNOWN_PATCH_HASHES = @{
    "a-stock-data|3.5.1+uzi.1" = "7d807dfc893c584f7bd188c88ca13308efc7a83b4a31aed33509e84887e6d1f7"
}

function Get-GitHubLatestRelease([string]$Repo) {
    $uri = "https://api.github.com/repos/$Repo/releases/latest"
    return Invoke-RestMethod -Uri $uri -Headers @{"User-Agent"="UZI-Windows-Upstream-Auditor"} -TimeoutSec 20
}

function Get-GitHubReleaseHeadState([string]$Repo, [string]$Tag) {
    $headers = @{"User-Agent"="UZI-Windows-Upstream-Auditor"}
    $releaseCommit = Invoke-RestMethod `
        -Uri "https://api.github.com/repos/$Repo/commits/$Tag" `
        -Headers $headers -TimeoutSec 20
    $headCommit = Invoke-RestMethod `
        -Uri "https://api.github.com/repos/$Repo/commits/main" `
        -Headers $headers -TimeoutSec 20
    $compare = Invoke-RestMethod `
        -Uri "https://api.github.com/repos/$Repo/compare/$Tag...main" `
        -Headers $headers -TimeoutSec 20
    return [ordered]@{
        release_commit = [string]$releaseCommit.sha
        head_commit = [string]$headCommit.sha
        head_commit_date = [string]$headCommit.commit.committer.date
        release_is_head = ([string]$releaseCommit.sha -eq [string]$headCommit.sha)
        commits_after_release = [int]$compare.ahead_by
    }
}

function Get-InstalledSkillVersion([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    $match = Select-String -LiteralPath $Path -Pattern '^version:\s*(.+)$' | Select-Object -First 1
    if ($null -eq $match) { return $null }
    return $match.Matches[0].Groups[1].Value.Trim()
}

function Get-Sha256([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-ReleaseSkill([string]$Repo, [string]$Name, [string]$TempRoot) {
    $release = Get-GitHubLatestRelease $Repo
    $tag = [string]$release.tag_name
    if ([string]::IsNullOrWhiteSpace($tag)) { throw "$Repo latest release has no tag" }
    $releaseHead = Get-GitHubReleaseHeadState $Repo $tag

    $download = Join-Path $TempRoot "$Name-SKILL.md"
    # Resolve the tag once, then download by immutable commit SHA.  This avoids
    # a time-of-check/time-of-use gap if a tag is moved after the API response.
    $uri = "https://raw.githubusercontent.com/$Repo/$($releaseHead.release_commit)/SKILL.md"
    Invoke-WebRequest -Uri $uri -OutFile $download -Headers @{"User-Agent"="UZI-Windows-Upstream-Auditor"} -TimeoutSec 30

    $declared = Get-InstalledSkillVersion $download
    $normalizedTag = $tag.TrimStart('v')
    if ($declared -ne $normalizedTag) {
        throw "$Repo release tag $tag does not match SKILL.md version $declared"
    }
    return [ordered]@{
        repo = $Repo
        name = $Name
        tag = $tag
        published_at = [string]$release.published_at
        release_url = [string]$release.html_url
        release_commit = $releaseHead.release_commit
        head_commit = $releaseHead.head_commit
        head_commit_date = $releaseHead.head_commit_date
        release_is_head = $releaseHead.release_is_head
        commits_after_release = $releaseHead.commits_after_release
        download_path = $download
        sha256 = Get-Sha256 $download
    }
}

function Get-UziState {
    Set-Location $UZI_ROOT
    $branch = (git branch --show-current).Trim()
    $status = @(git status --porcelain)

    git fetch upstream main --quiet
    if ($LASTEXITCODE -ne 0) { throw "git fetch upstream main failed" }

    $upstreamHead = (git rev-parse upstream/main).Trim()
    $counts = ((git rev-list --left-right --count HEAD...upstream/main).Trim() -split '\s+')
    return [ordered]@{
        branch = $branch
        head = (git rev-parse HEAD).Trim()
        clean = ($status.Count -eq 0)
        upstream_main = $upstreamHead
        ahead_of_upstream = [int]$counts[0]
        behind_upstream = [int]$counts[1]
        upstream_push_url = (git remote get-url --push upstream).Trim()
    }
}

function Install-ReleaseSkill([System.Collections.IDictionary]$Skill, [string]$BackupDir) {
    $targetDir = Join-Path $SKILL_ROOT $Skill.name
    $target = Join-Path $targetDir "SKILL.md"
    New-Item -ItemType Directory -Force -Path $targetDir | Out-Null

    if (Test-Path -LiteralPath $target) {
        $skillBackupDir = Join-Path $BackupDir $Skill.name
        New-Item -ItemType Directory -Force -Path $skillBackupDir | Out-Null
        Copy-Item -LiteralPath $target -Destination (Join-Path $skillBackupDir "SKILL.md")
    }

    Copy-Item -LiteralPath $Skill.download_path -Destination $target -Force
    if ((Get-Sha256 $target) -ne $Skill.sha256) {
        throw "$($Skill.name) post-copy hash mismatch"
    }
}

$startedAt = Get-Date
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("uzi-upstream-audit-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tempRoot | Out-Null

try {
    Write-Host "=== UZI upstream audit (non-destructive) ==="
    $uzi = Get-UziState
    $skills = @(
        Get-ReleaseSkill "simonlin1212/a-stock-data" "a-stock-data" $tempRoot
        Get-ReleaseSkill "simonlin1212/global-stock-data" "global-stock-data" $tempRoot
    )

    foreach ($skill in $skills) {
        $installed = Join-Path (Join-Path $SKILL_ROOT $skill.name) "SKILL.md"
        $skill["installed_version"] = Get-InstalledSkillVersion $installed
        $skill["installed_sha256"] = Get-Sha256 $installed
        $skill["matches_latest_release"] = ($skill.installed_sha256 -eq $skill.sha256)
        $releaseVersion = $skill.tag.TrimStart('v')
        $patchKey = "$($skill.name)|$($skill.installed_version)"
        $knownPatchHash = $KNOWN_PATCH_HASHES[$patchKey]
        $skill["protected_local_patch"] = (
            $skill.installed_version -like "$releaseVersion+uzi.*" -and
            -not [string]::IsNullOrWhiteSpace($knownPatchHash) -and
            $skill.installed_sha256 -eq $knownPatchHash
        )
        $skill["unverified_local_patch"] = (
            $skill.installed_version -like "$releaseVersion+uzi.*" -and
            -not $skill.protected_local_patch
        )
        Write-Host ("{0}: installed={1}, latest={2}, exact={3}" -f $skill.name, $skill.installed_version, $skill.tag, $skill.matches_latest_release)
        Write-Host ("  release={0}, head={1}, after-release={2}" -f `
            $skill.release_commit.Substring(0, 7), `
            $skill.head_commit.Substring(0, 7), `
            $skill.commits_after_release)
        if ($skill.protected_local_patch) {
            Write-Host ("  protected local patch: {0}" -f $skill.installed_version)
        }
        if ($skill.unverified_local_patch) {
            Write-Warning ("Unverified local patch hash; ApplySkills will replace it: {0}" -f $skill.installed_version)
        }
    }

    Write-Host ("UZI: branch={0}, ahead={1}, behind={2}, clean={3}" -f $uzi.branch, $uzi.ahead_of_upstream, $uzi.behind_upstream, $uzi.clean)
    if ($uzi.upstream_push_url -ne "DISABLED") {
        Write-Warning "upstream push URL is not DISABLED: $($uzi.upstream_push_url)"
    }

    if ($Mode -eq "ApplySkills") {
        $backupDir = Join-Path $BACKUP_ROOT $startedAt.ToString("yyyyMMdd_HHmmss")
        foreach ($skill in $skills) {
            if (-not $skill.matches_latest_release -and -not $skill.protected_local_patch) {
                Install-ReleaseSkill $skill $backupDir
                $installed = Join-Path (Join-Path $SKILL_ROOT $skill.name) "SKILL.md"
                $skill.installed_version = Get-InstalledSkillVersion $installed
                $skill.installed_sha256 = Get-Sha256 $installed
                $skill.matches_latest_release = ($skill.installed_sha256 -eq $skill.sha256)
                $skill.protected_local_patch = $false
                $skill.unverified_local_patch = $false
                Write-Host "Updated $($skill.name) to immutable release $($skill.tag)"
            }
        }
    } else {
        Write-Host "Audit only: no skill, branch, dependency, or working-tree content was changed."
    }

    $state = [ordered]@{
        checked_at = $startedAt.ToString("yyyy-MM-dd HH:mm:ss")
        mode = $Mode
        uzi = $uzi
        skills = $skills | ForEach-Object {
            [ordered]@{
                repo = $_.repo
                tag = $_.tag
                published_at = $_.published_at
                release_url = $_.release_url
                release_commit = $_.release_commit
                head_commit = $_.head_commit
                head_commit_date = $_.head_commit_date
                release_is_head = $_.release_is_head
                commits_after_release = $_.commits_after_release
                installed_version = $_.installed_version
                installed_sha256 = $_.installed_sha256
                release_sha256 = $_.sha256
                matches_latest_release = $_.matches_latest_release
                protected_local_patch = $_.protected_local_patch
                unverified_local_patch = $_.unverified_local_patch
            }
        }
        policy = [ordered]@{
            default_is_audit_only = $true
            uzi_auto_merge = $false
            dependency_auto_install = $false
            skill_source_is_immutable_release = $true
        }
    }
    $state | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $STATE_FILE -Encoding UTF8
    Write-Host "State: $STATE_FILE"
    Write-Host "UZI code is never reset or merged by this script; use an isolation branch and validation gates."
} finally {
    if (Test-Path -LiteralPath $tempRoot) {
        $resolvedTemp = [System.IO.Path]::GetFullPath($tempRoot)
        $resolvedBase = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
        $leaf = Split-Path -Leaf $resolvedTemp
        if ($resolvedTemp.StartsWith($resolvedBase, [System.StringComparison]::OrdinalIgnoreCase) -and $leaf.StartsWith("uzi-upstream-audit-")) {
            Remove-Item -LiteralPath $resolvedTemp -Recurse -Force
        } else {
            throw "Refusing to remove unexpected temp path: $resolvedTemp"
        }
    }
    Set-Location $UZI_ROOT
}
