Attribute VB_Name = "CostCurve"
' Crude-oil supply cost curve - VBA module for the Excel workbook (model.xlsx).
' Mirrors the SUMIF logic on the Outputs sheet and the Python/JS engines, so the same
' figures can be produced natively in Excel with macros. Import via the VBA editor
' (File > Import File...) and use the functions as worksheet formulas or in macros.
Option Explicit

' Volume whose full-cycle (or cash) breakeven exceeds the oil price:
' the "new-investment at risk" (or shut-in) view. Same as SUMIF(breakeven, ">"&price, production).
Public Function AtRiskVolume(production As Range, breakeven As Range, price As Double) As Double
    Dim i As Long, total As Double
    For i = 1 To production.Cells.Count
        If breakeven.Cells(i).Value > price Then total = total + production.Cells(i).Value
    Next i
    AtRiskVolume = total
End Function

' Economic volume (breakeven at or below the price).
Public Function EconomicVolume(production As Range, breakeven As Range, price As Double) As Double
    Dim i As Long, total As Double
    For i = 1 To production.Cells.Count
        If breakeven.Cells(i).Value <= price Then total = total + production.Cells(i).Value
    Next i
    EconomicVolume = total
End Function

' Marginal (market-clearing) cost to meet a demand volume, walking the cost-sorted curve.
' Requires production/breakeven sorted ascending by breakeven (as on the CostCurve sheet).
Public Function MarginalBarrel(production As Range, breakeven As Range, demandMmbd As Double) As Double
    Dim i As Long, cum As Double
    For i = 1 To production.Cells.Count
        cum = cum + production.Cells(i).Value
        If demandMmbd <= cum Then
            MarginalBarrel = breakeven.Cells(i).Value
            Exit Function
        End If
    Next i
    ' demand exceeds modelled supply -> return the most expensive barrel
    MarginalBarrel = breakeven.Cells(breakeven.Cells.Count).Value
End Function
