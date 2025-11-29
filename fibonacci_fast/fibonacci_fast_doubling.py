def fibonacci_fast_doubling(n, mod=10**100):
    """
    Calcula el n-ésimo número de Fibonacci usando el algoritmo de Fast Doubling.
    Devuelve el resultado módulo 10^100 para obtener solo los últimos 100 dígitos.
    """
    if n == 0:
        return 0
    if n == 1:
        return 1

    def fib_pair(k):
        """
        Devuelve (F(k), F(k+1)) usando Fast Doubling.
        """
        if k == 0:
            return 0, 1
        if k == 1:
            return 1, 1

        if k % 2 == 0:
            # k es par: k = 2m
            m = k // 2
            f_m, f_m1 = fib_pair(m)
            # F(2m) = F(m) * [2*F(m+1) - F(m)]
            # F(2m+1) = F(m+1)^2 + F(m)^2
            f_2m = (f_m * (2 * f_m1 - f_m)) % mod
            f_2m1 = (f_m1 * f_m1 + f_m * f_m) % mod
            return f_2m, f_2m1
        else:
            # k es impar: k = 2m+1
            m = k // 2
            f_m, f_m1 = fib_pair(m)
            # F(2m+1) = F(m+1)^2 + F(m)^2
            # F(2m+2) = F(2m+1) + F(2m)
            f_2m1 = (f_m1 * f_m1 + f_m * f_m) % mod
            f_2m2 = (f_2m1 + f_m * (2 * f_m1 - f_m)) % mod
            return f_2m1, f_2m2

    # Calculamos (F(n), F(n+1)) y devolvemos F(n)
    result, _ = fib_pair(n)
    return result

# Parámetro: n = 500,000
n = 500000
last_100_digits = fibonacci_fast_doubling(n)

# Imprimir solo los últimos 100 dígitos
print(last_100_digits)