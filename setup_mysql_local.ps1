$ErrorActionPreference = 'Continue'
$root = 'C:\Users\Am\EMP-System-1'
$mysqlRoot = Join-Path $root 'mysql_local'
$zipPath = Join-Path $mysqlRoot 'mysql.zip'
$logPath = Join-Path $root 'mysql_setup_log.txt'

New-Item -ItemType Directory -Force -Path $mysqlRoot | Out-Null
"START $(Get-Date -Format o)" | Out-File -FilePath $logPath -Encoding utf8

$urls = @(
    'https://dev.mysql.com/get/Downloads/MySQL-8.0/mysql-8.0.40-winx64.zip',
    'https://cdn.mysql.com/Downloads/MySQL-8.0/mysql-8.0.40-winx64.zip'
)

$downloaded = $false
foreach ($u in $urls) {
    try {
        "Trying $u" | Out-File -FilePath $logPath -Encoding utf8 -Append
        Invoke-WebRequest -Uri $u -OutFile $zipPath -UseBasicParsing
        if (Test-Path $zipPath) {
            $downloaded = $true
            "Downloaded $zipPath size=$((Get-Item $zipPath).Length)" | Out-File -FilePath $logPath -Encoding utf8 -Append
            break
        }
    }
    catch {
        "ERROR $($u) : $($_.Exception.Message)" | Out-File -FilePath $logPath -Encoding utf8 -Append
    }
}

if (-not $downloaded) {
    "DOWNLOAD_FAILED" | Out-File -FilePath $logPath -Encoding utf8 -Append
    exit 1
}

Expand-Archive -Path $zipPath -DestinationPath $mysqlRoot -Force
"Expanded archive" | Out-File -FilePath $logPath -Encoding utf8 -Append

$extracted = Get-ChildItem -Path $mysqlRoot -Directory | Sort-Object Name
foreach ($d in $extracted) {
    "FOUND_DIR $($d.FullName)" | Out-File -FilePath $logPath -Encoding utf8 -Append
}

$baseDir = $extracted | Where-Object { $_.Name -match 'mysql-8\.' } | Select-Object -First 1
if (-not $baseDir) {
    "NO_MYSQL_BASE_DIR" | Out-File -FilePath $logPath -Encoding utf8 -Append
    exit 2
}

$basePath = $baseDir.FullName
$dataDir = Join-Path $root 'mysql_local\data'
$iniPath = Join-Path $basePath 'my.ini'
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null

@"
[mysqld]
basedir=$basePath
bind-address=127.0.0.1
port=3306
datadir=$dataDir
default_authentication_plugin=mysql_native_password
socket=$dataDir\mysql.sock
log-error=$dataDir\mysql.err
transaction-isolation=READ-COMMITTED
"@ | Set-Content -Path $iniPath -Encoding ASCII

"Prepared my.ini" | Out-File -FilePath $logPath -Encoding utf8 -Append

$initCmd = "& '$basePath\bin\mysqld.exe' --defaults-file='$iniPath' --initialize-insecure --console"
$initOutput = Invoke-Expression $initCmd 2>&1
$initOutput | Out-File -FilePath $logPath -Encoding utf8 -Append

$startCmd = "Start-Process -FilePath '$basePath\bin\mysqld.exe' -ArgumentList '--defaults-file=$iniPath' -NoNewWindow -PassThru"
try {
    $proc = Invoke-Expression $startCmd
    "STARTED_PID=$($proc.Id)" | Out-File -FilePath $logPath -Encoding utf8 -Append
}
catch {
    "START_ERROR $($_.Exception.Message)" | Out-File -FilePath $logPath -Encoding utf8 -Append
}

$client = Join-Path $basePath 'bin\mysql.exe'
$rootUser = 'root'
$pass = ''
$mysqlCmd = "& '$client' -uroot --protocol=TCP -P3306 -e \"ALTER USER '$rootUser'@'localhost' IDENTIFIED BY 'root'; CREATE DATABASE IF NOT EXISTS emp_system; GRANT ALL PRIVILEGES ON emp_system.* TO '$rootUser'@'localhost'; FLUSH PRIVILEGES;\""
try {
    $out = Invoke-Expression $mysqlCmd 2>&1
    $out | Out-File -FilePath $logPath -Encoding utf8 -Append
    "MYSQL_SETUP_DONE" | Out-File -FilePath $logPath -Encoding utf8 -Append
}
catch {
    "MYSQL_SETUP_ERROR $($_.Exception.Message)" | Out-File -FilePath $logPath -Encoding utf8 -Append
}

"FINISHED $(Get-Date -Format o)" | Out-File -FilePath $logPath -Encoding utf8 -Append
