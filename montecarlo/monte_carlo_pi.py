"""
Programa para estimar el valor de π usando el método de Monte Carlo.
Genera 1,000,000 puntos aleatorios en un plano 2D y determina cuántos caen dentro de un círculo unitario.
Calcula π basado en la proporción y compara con el valor real math.pi.
Opcional: Se usa numpy para vectorizar la operación y mejorar el rendimiento.
"""

import numpy as np
import math

# Número de puntos a generar
num_points = 1_000_000

# Generar puntos aleatorios en el cuadrado [-1, 1] x [-1, 1]
# Esto se hace con numpy para vectorizar la operación
points = np.random.uniform(-1, 1, (num_points, 2))

# Calcular la distancia al origen para cada punto (x^2 + y^2)
distances_squared = np.sum(points**2, axis=1)

# Contar cuántos puntos caen dentro del círculo unitario (distancia <= 1)
inside_circle = distances_squared <= 1
num_inside = np.sum(inside_circle)

# Estimar pi: (número de puntos dentro del círculo / total) * 4
estimated_pi = (num_inside / num_points) * 4

# Valor real de pi
real_pi = math.pi

# Calcular el porcentaje de error
error_percentage = abs((estimated_pi - real_pi) / real_pi) * 100

# Mostrar resultados
print(f"Número de puntos generados: {num_points}")
print(f"Puntos dentro del círculo: {num_inside}")
print(f"Estimación de pi: {estimated_pi}")
print(f"Valor real de pi: {real_pi}")
print(f"Porcentaje de error: {error_percentage:.6f}%")