"""
Programa de Amortización de Préstamos en Python
Este programa calcula la tabla de amortización de un préstamo
basado en los parámetros proporcionados.

Parámetros:
- monto: monto total del préstamo (en moneda local)
- tasa_interes_anual: tasa de interés anual en porcentaje (por ejemplo, 12 para 12%)
- plazo_anios: número de años del préstamo
- frecuencia_pago: frecuencia de pagos ('mensual', 'semestral', 'anual')
"""

import sys
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict


def calcular_amortizacion(monto: Decimal, tasa_interes_anual: float, plazo_anios: int, frecuencia_pago: str) -> List[Dict]:
    """
    Calcula la tabla de amortización de un préstamo.

    Args:
        monto: Monto total del préstamo (Decimal)
        tasa_interes_anual: Tasa de interés anual en porcentaje (float)
        plazo_anios: Número de años del préstamo (int)
        frecuencia_pago: Frecuencia de pagos ('mensual', 'semestral', 'anual')

    Returns:
        Lista de diccionarios con los detalles de cada pago
    """
    # Convertir tasa anual a tasa periódica
    if frecuencia_pago == 'mensual':
        n = 12
    elif frecuencia_pago == 'semestral':
        n = 2
    elif frecuencia_pago == 'anual':
        n = 1
    else:
        raise ValueError("Frecuencia de pago inválida. Debe ser 'mensual', 'semestral' o 'anual'.")

    tasa_periodica = Decimal(tasa_interes_anual) / Decimal(100) / Decimal(n)
    num_pagos = plazo_anios * n
    monto_decimal = monto

    # Calcular pago mensual (cuota fija)
    if tasa_periodica == 0:
        cuota = monto_decimal / num_pagos
    else:
        # Fórmula de cuota: P = [P * r * (1+r)^n] / [(1+r)^n - 1]
        r = tasa_periodica
        factor = (1 + r) ** num_pagos
        cuota = (monto_decimal * r * factor) / (factor - 1)

    cuota = cuota.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # Inicializar tabla de amortización
    tabla = []
    saldo_restante = monto_decimal

    for i in range(1, num_pagos + 1):
        # Interés del periodo
        interes = saldo_restante * tasa_periodica
        interes = interes.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # Capital pagado
        capital = cuota - interes

        # Actualizar saldo
        saldo_restante -= capital

        # Añadir registro a la tabla
        tabla.append({
            'periodo': i,
            'cuota': float(cuota),
            'interes': float(interes),
            'capital': float(capital),
            'saldo_restante': float(saldo_restante)
        })

        # Asegurarse de que el saldo final sea cero (por redondeo)
        if i == num_pagos:
            tabla[i-1]['saldo_restante'] = 0.0

    return tabla


def imprimir_tabla_amortizacion(tabla: List[Dict], monto: Decimal, tasa_interes_anual: float, plazo_anios: int, frecuencia_pago: str):
    """
    Imprime la tabla de amortización en formato legible.
    """
    print("\n" + "="*80)
    print("              TABLA DE AMORTIZACIÓN DE PRÉSTAMO")
    print("="*80)
    print(f"Monto del préstamo: ${monto:,.2f}")
    print(f"Tasa de interés anual: {tasa_interes_anual}%")
    print(f"Plazo: {plazo_anios} años")
    print(f"Frecuencia de pago: {frecuencia_pago.capitalize()}")
    print("-"*80)
    print(f"{'Periodo':<8} {'Cuota':<12} {'Interés':<12} {'Capital':<12} {'Saldo Restante':<15}")
    print("-"*80)

    for registro in tabla:
        print(f"{registro['periodo']:<8} "
               f"${registro['cuota']:>11.2f} "
               f"${registro['interes']:>11.2f} "
               f"${registro['capital']:>11.2f} "
               f"${registro['saldo_restante']:>14.2f}")

    print("-"*80)
    print(f"Total pagado: ${sum(r['cuota'] for r in tabla):,.2f}")
    print(f"Total intereses pagados: ${sum(r['interes'] for r in tabla):,.2f}")
    print(f"Total capital pagado: ${sum(r['capital'] for r in tabla):,.2f}")
    print("="*80)


def main():
    """
    Función principal que maneja la entrada de parámetros y ejecuta el cálculo.
    """
    # Verificar si se pasaron argumentos
    if len(sys.argv) < 5:
        print("Uso: python amortizacion.py <monto> <tasa_anual> <plazo_anios> <frecuencia_pago>")
        print("Ejemplo: python amortizacion.py 100000 12 5 mensual")
        print("Frecuencias válidas: mensual, semestral, anual")
        return

    try:
        monto = Decimal(sys.argv[1])
        tasa_interes_anual = float(sys.argv[2])
        plazo_anios = int(sys.argv[3])
        frecuencia_pago = sys.argv[4].lower()

        if monto <= 0:
            raise ValueError("El monto debe ser mayor que cero.")
        if tasa_interes_anual < 0:
            raise ValueError("La tasa de interés no puede ser negativa.")
        if plazo_anios <= 0:
            raise ValueError("El plazo debe ser mayor que cero.")
        if frecuencia_pago not in ['mensual', 'semestral', 'anual']:
            raise ValueError("Frecuencia de pago no válida.")

        print(f"Calculando amortización para: monto={monto}, tasa={tasa_interes_anual}%, plazo={plazo_anios} años, frecuencia={frecuencia_pago}")

        # Calcular tabla
        tabla = calcular_amortizacion(monto, tasa_interes_anual, plazo_anios, frecuencia_pago)

        # Imprimir tabla
        imprimir_tabla_amortizacion(tabla, monto, tasa_interes_anual, plazo_anios, frecuencia_pago)

    except Exception as e:
        print(f"Error: {e}")
        print("Por favor, verifique los parámetros y vuelva a intentarlo.")


if __name__ == "__main__":
    main()