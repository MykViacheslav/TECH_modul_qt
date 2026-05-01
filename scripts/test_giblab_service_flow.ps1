param(
  [int]$ProjectId = 1,
  [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

function Assert-True {
  param(
    [bool]$Condition,
    [string]$Message
  )
  if (-not $Condition) {
    throw "ASSERT FAILED: $Message"
  }
}

Write-Host "[TEST] GIBLAB service flow: start" -ForegroundColor Cyan

# 1) backend connectivity
$summary = Invoke-RestMethod -Uri "$BaseUrl/system/summary"
Assert-True ($null -ne $summary) "Backend unavailable at $BaseUrl"

# 2) get materials (must exist for service + edge)
$materials = @(Invoke-RestMethod -Uri "$BaseUrl/db/materials")
Assert-True ($materials.Count -gt 0) "No materials in database"
$material = $materials[0]

$price = 22.5
if ($material.PSObject.Properties.Name -contains "price") {
  try {
    $price = [double]$material.price
  } catch {
    $price = 22.5
  }
}

# 3) preview service pricing with edge
$pricingInput = @{
  schema_version = "service_pricing_payload_v1"
  service_mode = "service-cut-edge"
  service_subtype = "service-cut-edge"
  base_material_id = [string]$material.id
  base_material_name = "Bialy Diament"
  base_material_price_m2 = $price
  base_thickness_mm = 18
  length_mm = 2000
  width_mm = 600
  quantity = 1
  edge_mode = "default"
  edge_default_material_id = [string]$material.id
  edge_top = $true
  edge_bottom = $false
  edge_left = $false
  edge_right = $true
  cnc_pattern = "line"
  lacquer = $false
  lacquer_sides = 1
  veneer_sides = 1
  veneer_lacquer = $false
  bent_shape = "arc"
  bent_radius_mm = 0
  bent_complexity = 1
  extra_layers = @()
}

$previewPayload = @{ item = $pricingInput } | ConvertTo-Json -Depth 10 -Compress
$preview = Invoke-RestMethod -Uri "$BaseUrl/api/service-pricing/preview" -Method Post -Body $previewPayload -ContentType "application/json"
Assert-True ($preview.result.pricing_status -eq "ready") "Pricing preview is not ready"

# 4) create order with one position + two formatki
$positionId = [guid]::NewGuid().ToString()
$formatka1Id = [guid]::NewGuid().ToString()
$formatka2Id = [guid]::NewGuid().ToString()
$now = Get-Date -Format "yyyyMMdd_HHmmss"
$title = "TEST_GIBLAB_FLOW_$now"

$formatka2Input = $pricingInput.Clone()
$formatka2Input.length_mm = 1200
$formatka2Input.width_mm = 400
$formatka2Input.quantity = 2

$spec = @{
  unified_service_row_schema_version = "service_pricing_payload_v1"
  valuation_method = "service-cut-edge"
  positions = @(
    @{
      id = $positionId
      name = "TEST GIBLAB POZYCJA"
      type = "Usluga"
      quantity = 1
      vat = 23
      description = "test pozycja + formatki + okleina"
      textureOrColor = ""
      purchaseType = "invoice"
      serviceMode = "service-cut-edge"
      sourceType = "manual"
      baseMaterialName = "Bialy Diament"
      lengthMm = 2000
      widthMm = 600
      thicknessMm = 18
      edgeTop = $true
      edgeBottom = $false
      edgeLeft = $false
      edgeRight = $true
      servicePricingInput = $pricingInput
      serviceFormatki = @(
        @{
          id = $formatka1Id
          name = "Formatka A"
          quantity = 1
          description = "pierwsza formatka"
          servicePricingInput = $pricingInput
        },
        @{
          id = $formatka2Id
          name = "Formatka B"
          quantity = 2
          description = "druga formatka"
          servicePricingInput = $formatka2Input
        }
      )
    }
  )
}

$createPayload = @{
  project_id = $ProjectId
  client_name = "Klient demo"
  title = $title
  deadline = ""
  deadline_from = ""
  deadline_to = ""
  budget = 0
  status = "Nowe"
  spec_json = ($spec | ConvertTo-Json -Depth 20 -Compress)
}

$created = Invoke-RestMethod -Uri "$BaseUrl/orders" -Method Post -Body ($createPayload | ConvertTo-Json -Depth 20 -Compress) -ContentType "application/json"
Assert-True ($created.id -gt 0) "Order was not created"

# 5) verify persisted order payload
$orders = @(Invoke-RestMethod -Uri "$BaseUrl/orders?project_id=$ProjectId")
$order = $orders | Where-Object { $_.id -eq $created.id } | Select-Object -First 1
Assert-True ($null -ne $order) "Created order not found in /orders list"

$saved = $order.spec_json | ConvertFrom-Json
$savedPos = @($saved.positions)[0]
$savedFormatki = @($savedPos.serviceFormatki)

Assert-True ($savedPos.name -eq "TEST GIBLAB POZYCJA") "Position name mismatch"
Assert-True ([string]$savedPos.servicePricingInput.edge_default_material_id -eq [string]$material.id) "Edge material ID mismatch"
Assert-True ([bool]$savedPos.servicePricingInput.edge_top) "Edge top should be true"
Assert-True ([bool]$savedPos.servicePricingInput.edge_right) "Edge right should be true"
Assert-True ($savedFormatki.Count -eq 2) "Expected exactly 2 formatki"
Assert-True ($savedFormatki[1].name -eq "Formatka B") "Second formatka name mismatch"
Assert-True ([int]$savedFormatki[1].quantity -eq 2) "Second formatka quantity mismatch"
Assert-True ([int]$savedFormatki[1].servicePricingInput.length_mm -eq 1200) "Second formatka length mismatch"
Assert-True ([int]$savedFormatki[1].servicePricingInput.width_mm -eq 400) "Second formatka width mismatch"

Write-Host "[TEST] PASS" -ForegroundColor Green
Write-Host ("order_id={0} title={1} material={2} formatki={3}" -f $created.id, $title, $savedPos.baseMaterialName, $savedFormatki.Count)
