# Windows 定时任务配置脚本
# 每天自动运行 GitHub Trending → Notion 脚本

# 获取当前脚本所在目录
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonScript = Join-Path $scriptPath "github_trending_notion.py"

# 检查Python是否安装
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "错误: 未找到Python，请先安装Python 3.7+" -ForegroundColor Red
    exit 1
}

Write-Host "Python路径: $($pythonCmd.Source)" -ForegroundColor Green

# 删除已存在的同名任务（如果存在）
$taskName = "GitHubTrendingToNotion"
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "删除已存在的定时任务..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# 创建新的定时任务（每天早上9点运行）
$action = New-ScheduledTaskAction -Execute "python" -Argument $pythonScript -WorkingDirectory $scriptPath
$trigger = New-ScheduledTaskTrigger -Daily -At "09:00"
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "每天自动获取GitHub热门项目到Notion"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "定时任务创建成功!" -ForegroundColor Green
Write-Host "任务名称: $taskName" -ForegroundColor White
Write-Host "运行时间: 每天 09:00" -ForegroundColor White
Write-Host "脚本路径: $pythonScript" -ForegroundColor White
Write-Host ""
Write-Host "提示: 使用 'taskschd.msc' 打开任务计划程序查看或修改" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
