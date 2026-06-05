param(
    [string]$InputCsv = (Join-Path $PSScriptRoot 'model_results_comparison.csv'),
    [string]$OutputPng = (Join-Path $PSScriptRoot 'model_results_comparison_table.png')
)

Add-Type -AssemblyName System.Drawing

$rows = Import-Csv -Path $InputCsv | Sort-Object { [int]$_.rank_by_best_mAP50_95 }
if (-not $rows) {
    throw "No model result rows found in $InputCsv"
}

function New-Color([string]$hex) {
    return [System.Drawing.ColorTranslator]::FromHtml($hex)
}

function New-Font([float]$size, [System.Drawing.FontStyle]$style = [System.Drawing.FontStyle]::Regular) {
    return [System.Drawing.Font]::new('Segoe UI', $size, $style, [System.Drawing.GraphicsUnit]::Pixel)
}

function Draw-Text {
    param(
        [System.Drawing.Graphics]$Graphics,
        [string]$Text,
        [System.Drawing.Font]$Font,
        [System.Drawing.Brush]$Brush,
        [float]$X,
        [float]$Y,
        [float]$Width,
        [float]$Height,
        [System.Drawing.StringAlignment]$Alignment = [System.Drawing.StringAlignment]::Near
    )

    $format = [System.Drawing.StringFormat]::new()
    $format.Alignment = $Alignment
    $format.LineAlignment = [System.Drawing.StringAlignment]::Center
    $format.Trimming = [System.Drawing.StringTrimming]::EllipsisCharacter
    $format.FormatFlags = [System.Drawing.StringFormatFlags]::NoWrap
    $rect = [System.Drawing.RectangleF]::new($X, $Y, $Width, $Height)
    $Graphics.DrawString($Text, $Font, $Brush, $rect, $format)
    $format.Dispose()
}

function Model-Label([string]$run) {
    switch ($run) {
        'density_v5_lightaug' { return 'Density V5 - light augmentation' }
        'density_v6_improved' { return 'Density V6 - improved' }
        'multichannel_density_hag_dbh' { return 'Multichannel - from YOLO11n' }
        'multichannel_from_density_best' { return 'Multichannel - from Density V5 best' }
        'multichannel_from_density_v6_best' { return 'Multichannel - from Density V6 best' }
        'multichannel_from_v5_v6hyp' { return 'Multichannel - V5 init + V6 hyperparams' }
        default { return $run }
    }
}

function Input-Label([string]$group) {
    if ($group -eq 'biomass2_multichannel') {
        return 'RGB: Density + HAG + DBH-band'
    }
    return 'Density only'
}

function Init-Label([string]$source) {
    if ($source -match 'density_v5_lightaug') {
        return 'Density V5 best'
    }
    if ($source -match 'density_v6_improved') {
        return 'Density V6 best'
    }
    return 'YOLO11n'
}

function Value([object]$row, [string]$property) {
    return ([double]$row.$property).ToString('0.00000')
}

$width = 2560
$height = 1440
$margin = 96
$tableX = $margin
$tableY = 355
$headerHeight = 84
$rowHeight = 122
$tableWidth = $width - (2 * $margin)

$columns = @(
    @{ Label = '#'; Width = 74; Alignment = [System.Drawing.StringAlignment]::Center },
    @{ Label = 'MODEL / EXPERIMENT'; Width = 580; Alignment = [System.Drawing.StringAlignment]::Near },
    @{ Label = 'INPUT CHANNELS'; Width = 380; Alignment = [System.Drawing.StringAlignment]::Near },
    @{ Label = 'INIT'; Width = 235; Alignment = [System.Drawing.StringAlignment]::Near },
    @{ Label = 'BEST mAP50'; Width = 212; Alignment = [System.Drawing.StringAlignment]::Center },
    @{ Label = 'BEST mAP50-95'; Width = 248; Alignment = [System.Drawing.StringAlignment]::Center },
    @{ Label = 'FINAL P'; Width = 175; Alignment = [System.Drawing.StringAlignment]::Center },
    @{ Label = 'FINAL R'; Width = 175; Alignment = [System.Drawing.StringAlignment]::Center },
    @{ Label = 'FINAL mAP50-95'; Width = 289; Alignment = [System.Drawing.StringAlignment]::Center }
)

$bestPeak = ($rows | Measure-Object -Property best_mAP50_95 -Maximum).Maximum
$bestFinal = ($rows | Measure-Object -Property final_mAP50_95 -Maximum).Maximum
$bestMap50 = ($rows | Measure-Object -Property best_mAP50 -Maximum).Maximum

$bitmap = [System.Drawing.Bitmap]::new($width, $height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit
$graphics.Clear((New-Color '#F7F9FC'))

$navy = New-Color '#10243E'
$muted = New-Color '#52657A'
$line = New-Color '#D9E1EA'
$header = New-Color '#142B49'
$white = New-Color '#FFFFFF'
$densityRow = New-Color '#FFFFFF'
$multiRow = New-Color '#F1F8F8'
$peakFill = New-Color '#087F5B'
$finalFill = New-Color '#007C91'
$accent = New-Color '#0B8494'

$titleFont = New-Font 55 ([System.Drawing.FontStyle]::Bold)
$subtitleFont = New-Font 24
$metaFont = New-Font 22
$headerFont = New-Font 20 ([System.Drawing.FontStyle]::Bold)
$labelFont = New-Font 24 ([System.Drawing.FontStyle]::Bold)
$runFont = New-Font 17
$cellFont = New-Font 22
$cellBoldFont = New-Font 22 ([System.Drawing.FontStyle]::Bold)
$footerFont = New-Font 20

$navyBrush = [System.Drawing.SolidBrush]::new($navy)
$mutedBrush = [System.Drawing.SolidBrush]::new($muted)
$whiteBrush = [System.Drawing.SolidBrush]::new($white)
$headerBrush = [System.Drawing.SolidBrush]::new($header)
$linePen = [System.Drawing.Pen]::new($line, 1)
$accentPen = [System.Drawing.Pen]::new($accent, 7)

$graphics.DrawLine($accentPen, $margin, 84, $margin, 174)
Draw-Text $graphics 'Individual Tree Detection Model Comparison' $titleFont $navyBrush ($margin + 26) 75 1900 68
Draw-Text $graphics 'Rubber plantation LiDAR top-view detection | validation-set comparison' $subtitleFont $mutedBrush ($margin + 28) 150 1900 42
Draw-Text $graphics 'Multichannel input: R = Density   G = HAG P95   B = DBH-band Density' $metaFont $mutedBrush $margin 242 1800 38
Draw-Text $graphics 'Ranking metric: Best mAP50-95' $metaFont $navyBrush 1920 242 544 38 ([System.Drawing.StringAlignment]::Far)

$headerRect = [System.Drawing.Rectangle]::new($tableX, $tableY, $tableWidth, $headerHeight)
$graphics.FillRectangle($headerBrush, $headerRect)

$x = $tableX
foreach ($column in $columns) {
    Draw-Text $graphics $column.Label $headerFont $whiteBrush $x $tableY $column.Width $headerHeight $column.Alignment
    $x += $column.Width
}

for ($i = 0; $i -lt $rows.Count; $i++) {
    $row = $rows[$i]
    $y = $tableY + $headerHeight + ($i * $rowHeight)
    $fill = if ($row.group -eq 'biomass2_multichannel') { $multiRow } else { $densityRow }
    $rowBrush = [System.Drawing.SolidBrush]::new($fill)
    $graphics.FillRectangle($rowBrush, $tableX, $y, $tableWidth, $rowHeight)
    $rowBrush.Dispose()
    $graphics.DrawLine($linePen, $tableX, $y + $rowHeight, $tableX + $tableWidth, $y + $rowHeight)

    $x = $tableX
    Draw-Text $graphics $row.rank_by_best_mAP50_95 $labelFont $navyBrush $x $y $columns[0].Width $rowHeight ([System.Drawing.StringAlignment]::Center)
    $x += $columns[0].Width

    Draw-Text $graphics (Model-Label $row.run) $labelFont $navyBrush ($x + 18) ($y + 23) ($columns[1].Width - 36) 38
    Draw-Text $graphics $row.run $runFont $mutedBrush ($x + 18) ($y + 66) ($columns[1].Width - 36) 30
    $x += $columns[1].Width

    Draw-Text $graphics (Input-Label $row.group) $cellFont $navyBrush ($x + 18) $y ($columns[2].Width - 36) $rowHeight
    $x += $columns[2].Width

    Draw-Text $graphics (Init-Label $row.source_model) $cellFont $navyBrush ($x + 18) $y ($columns[3].Width - 36) $rowHeight
    $x += $columns[3].Width

    $bestMap50Text = Value $row 'best_mAP50'
    if ([double]$row.best_mAP50 -eq [double]$bestMap50) {
        $bestMap50Brush = [System.Drawing.SolidBrush]::new((New-Color '#E6F4EF'))
        $graphics.FillRectangle($bestMap50Brush, $x + 22, $y + 34, $columns[4].Width - 44, 54)
        $bestMap50Brush.Dispose()
        Draw-Text $graphics $bestMap50Text $cellBoldFont $navyBrush $x $y $columns[4].Width $rowHeight ([System.Drawing.StringAlignment]::Center)
    } else {
        Draw-Text $graphics $bestMap50Text $cellFont $navyBrush $x $y $columns[4].Width $rowHeight ([System.Drawing.StringAlignment]::Center)
    }
    $x += $columns[4].Width

    $peakText = Value $row 'best_mAP50_95'
    if ([double]$row.best_mAP50_95 -eq [double]$bestPeak) {
        $peakBrush = [System.Drawing.SolidBrush]::new($peakFill)
        $graphics.FillRectangle($peakBrush, $x + 24, $y + 30, $columns[5].Width - 48, 62)
        $peakBrush.Dispose()
        Draw-Text $graphics $peakText $cellBoldFont $whiteBrush $x $y $columns[5].Width $rowHeight ([System.Drawing.StringAlignment]::Center)
    } else {
        Draw-Text $graphics $peakText $cellFont $navyBrush $x $y $columns[5].Width $rowHeight ([System.Drawing.StringAlignment]::Center)
    }
    $x += $columns[5].Width

    Draw-Text $graphics (Value $row 'final_precision') $cellFont $navyBrush $x $y $columns[6].Width $rowHeight ([System.Drawing.StringAlignment]::Center)
    $x += $columns[6].Width
    Draw-Text $graphics (Value $row 'final_recall') $cellFont $navyBrush $x $y $columns[7].Width $rowHeight ([System.Drawing.StringAlignment]::Center)
    $x += $columns[7].Width

    $finalText = Value $row 'final_mAP50_95'
    if ([double]$row.final_mAP50_95 -eq [double]$bestFinal) {
        $finalBrush = [System.Drawing.SolidBrush]::new($finalFill)
        $graphics.FillRectangle($finalBrush, $x + 34, $y + 30, $columns[8].Width - 68, 62)
        $finalBrush.Dispose()
        Draw-Text $graphics $finalText $cellBoldFont $whiteBrush $x $y $columns[8].Width $rowHeight ([System.Drawing.StringAlignment]::Center)
    } else {
        Draw-Text $graphics $finalText $cellFont $navyBrush $x $y $columns[8].Width $rowHeight ([System.Drawing.StringAlignment]::Center)
    }
}

$footerY = $tableY + $headerHeight + ($rows.Count * $rowHeight) + 48
$greenBrush = [System.Drawing.SolidBrush]::new($peakFill)
$tealBrush = [System.Drawing.SolidBrush]::new($finalFill)
$graphics.FillRectangle($greenBrush, $margin, $footerY + 5, 26, 26)
Draw-Text $graphics 'Highest Best mAP50-95 (peak performance)' $footerFont $mutedBrush ($margin + 40) $footerY 530 38
$graphics.FillRectangle($tealBrush, ($margin + 610), $footerY + 5, 26, 26)
Draw-Text $graphics 'Highest Final mAP50-95 (last epoch)' $footerFont $mutedBrush ($margin + 650) $footerY 560 38
Draw-Text $graphics 'Higher is better | Generated from model_results_comparison.csv' $footerFont $mutedBrush $margin ($footerY + 62) 1000 38

$directory = Split-Path -Parent $OutputPng
if (-not (Test-Path $directory)) {
    New-Item -ItemType Directory -Path $directory | Out-Null
}

$bitmap.Save($OutputPng, [System.Drawing.Imaging.ImageFormat]::Png)

$greenBrush.Dispose()
$tealBrush.Dispose()
$accentPen.Dispose()
$linePen.Dispose()
$headerBrush.Dispose()
$whiteBrush.Dispose()
$mutedBrush.Dispose()
$navyBrush.Dispose()
$titleFont.Dispose()
$subtitleFont.Dispose()
$metaFont.Dispose()
$headerFont.Dispose()
$labelFont.Dispose()
$runFont.Dispose()
$cellFont.Dispose()
$cellBoldFont.Dispose()
$footerFont.Dispose()
$graphics.Dispose()
$bitmap.Dispose()

Write-Output "Saved presentation table image to $OutputPng"
