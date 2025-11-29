import numpy as np
from scipy.special import gamma

# Definición de parámetros
R = 2  # Radio de la hiperesfera
n = 10  # Número de dimensiones
num_samples = 10**6  # Número de muestras para Monte Carlo

# 1. Fórmula analítica exacta del volumen de una hiperesfera
# V_n(R) = π^(n/2) / Γ(n/2 + 1) * R^n
volume_analytical = (np.pi ** (n / 2)) / gamma(n / 2 + 1) * (R ** n)

# 2. Simulación de Monte Carlo
# Generar puntos aleatorios en el hipercubo [-R, R]^n
points = np.random.uniform(-R, R, size=(num_samples, n))

# Calcular la distancia al origen para cada punto
distances_squared = np.sum(points ** 2, axis=1)

# Contar cuántos puntos están dentro de la hiperesfera
inside_sphere = distances_squared <= R ** 2
fraction_inside = np.mean(inside_sphere)

# Volumen del hipercubo: (2R)^n
volume_hypercube = (2 * R) ** n

# Estimar el volumen de la hiperesfera
volume_mc = fraction_inside * volume_hypercube

# Calcular el error relativo
relative_error = abs(volume_analytical - volume_mc) / volume_analytical

# Mostrar resultados
print(f"Volumen analítico (exacto): {volume_analytical:.6f}")
print(f"Volumen Monte Carlo: {volume_mc:.6f}")
print(f"Diferencia absoluta: {abs(volume_analytical - volume_mc):.6f}")
print(f"Error relativo: {relative_error:.6f}")

# Explicación en comentarios sobre la maldición de la dimensionalidad
"""
La simulación de Monte Carlo se vuelve menos eficiente en dimensiones altas debido a la 'maldición de la dimensionalidad'.
En dimensiones altas, la mayoría del volumen del hipercubo está concentrado en las esquinas, lejos del centro.
La fracción de puntos dentro de la hiperesfera disminuye exponencialmente con el número de dimensiones.
Por ejemplo, en 10D, la probabilidad de que un punto aleatorio esté dentro de la hiperesfera es pequeña,
lo que requiere un número muy grande de muestras para obtener una estimación precisa.
"""