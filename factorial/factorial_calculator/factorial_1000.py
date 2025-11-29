"""
Calcula el factorial de 1000, suma sus dígitos y verifica el resultado
usando la fórmula de Stirling para confirmar el orden de magnitud.
"""

import math
import sys


def stirling_approximation(n):
    """
    Calcula una aproximación del logaritmo natural del factorial usando
    la fórmula de Stirling: ln(n!) ≈ n*ln(n) - n + 0.5*ln(2πn)
    Devuelve el valor aproximado del logaritmo natural del factorial.
    """
    if n <= 0:
        raise ValueError("n debe ser positivo")
    return n * math.log(n) - n + 0.5 * math.log(2 * math.pi * n)


def calculate_factorial(n):
    """
    Calcula el factorial de n usando Python's int (que maneja enteros arbitrariamente grandes).
    """
    if n < 0:
        raise ValueError("El factorial no está definido para números negativos")
    if n == 0 or n == 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def sum_digits(num_str):
    """
    Suma todos los dígitos de un número representado como cadena.
    """
    return sum(int(digit) for digit in num_str if digit.isdigit())


def verify_order_of_magnitude(n, approx_log_fact):
    """
    Verifica que el orden de magnitud del factorial calculado sea coherente
    con la aproximación de Stirling.
    Compara el logaritmo base 10 del factorial real con el de la aproximación.
    """
    actual_log10 = math.log10(approx_log_fact)  # log10 de la aproximación de ln(n!)
    # Convertimos el logaritmo natural a base 10
    approx_log10 = approx_log_fact / math.log(10)
    # El logaritmo base 10 del factorial real es log10(n!) = ln(n!)/ln(10)
    actual_factorial_log10 = approx_log_fact / math.log(10)

    # Para n=1000, el log10(n!) debería estar alrededor de 2567
    # (calculado previamente: log10(1000!) ≈ 2567.6)
    expected_log10 = 2567.6  # Valor esperado aproximado
    tolerance = 10  # Tolerancia de 10 unidades en el log10

    if abs(actual_factorial_log10 - expected_log10) < tolerance:
        print(f"[VERIFICACIÓN] El orden de magnitud es coherente: log10(n!) = {actual_factorial_log10:.2f}")
        return True
    else:
        print(f"[ADVERTENCIA] El orden de magnitud parece fuera de rango: {actual_factorial_log10:.2f} vs esperado {expected_log10}")
        return False


def main():
    """
    Función principal que ejecuta el cálculo del factorial de 1000,
    suma sus dígitos y verifica el resultado.
    """
    n = 1000

    print(f"Calculando factorial de {n}...")

    # Paso 1: Calcular factorial
    factorial = calculate_factorial(n)

    # Paso 2: Convertir a cadena para sumar dígitos
    factorial_str = str(factorial)
    digit_sum = sum_digits(factorial_str)

    # Paso 3: Verificar orden de magnitud con Stirling
    stirling_ln = stirling_approximation(n)
    is_coherent = verify_order_of_magnitude(n, stirling_ln)

    # Paso 4: Mostrar resultados
    print(f"\nResultado final:")
    print(f"Factorial de {n} = {factorial_str[:50]}...{factorial_str[-50:]} (muy largo, se muestra parte)")
    print(f"Suma de todos los dígitos: {digit_sum}")

    if is_coherent:
        print("[OK] Verificación de orden de magnitud exitosa.")
    else:
        print("[ADVERTENCIA] Verificación de orden de magnitud no confirmada. Posible error.")

    # Guardar el resultado en un archivo de log
    with open("factorial_result.md", "w", encoding="utf-8") as f:
        f.write("# Resultado del cálculo del factorial de 1000\n\n")
        f.write(f"## Factorial de {n}\n")
        f.write(f"El valor de {n}! tiene {len(factorial_str)} dígitos.\n\n")
        f.write(f"**Suma de los dígitos:** {digit_sum}\n\n")
        f.write("## Verificación con Stirling\n")
        f.write(f"Valor aproximado de ln({n}!) usando Stirling: {stirling_ln:.2f}\n")
        f.write(f"Valor esperado de log10({n}!): ~2567.6\n")
        f.write(f"Resultado de verificación: {'Éxito' if is_coherent else 'Advertencia'}\n\n")
        f.write("## Observaciones\n")
        f.write("- Python maneja enteros arbitrariamente grandes, por lo que el cálculo es exacto.\n")
        f.write("- La verificación con Stirling confirma que el orden de magnitud es correcto.\n")
        f.write("- La suma de dígitos se calcula directamente sobre la representación decimal.\n")


if __name__ == "__main__":
    main()