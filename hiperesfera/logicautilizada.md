# Lógica Utilizada para Calcular el Volumen de una Hiperesfera en 10 Dimensiones

## Objetivo
Implementar dos métodos para calcular el volumen de una hiperesfera de radio \( R = 2 \) en 10 dimensiones:
1. **Fórmula analítica exacta** usando la función Gamma.
2. **Simulación de Monte Carlo** para aproximar el volumen.

## Implementación

### Fórmula Analítica
El volumen \( V_n(R) \) de una hiperesfera de radio \( R \) en \( n \) dimensiones se calcula como:
\[
V_n(R) = \frac{\pi^{n/2}}{\Gamma\left(\frac{n}{2} + 1\right)} R^n
\]
Para \( n = 10 \) y \( R = 2 \), se usa `scipy.special.gamma` para calcular \( \Gamma \).

### Simulación de Monte Carlo
Se generan puntos aleatorios dentro del hipercubo \([-2, 2]^{10}\), se verifica si están dentro de la hiperesfera usando la condición \( \sum_{i=1}^{10} x_i^2 \leq R^2 \). La proporción de puntos dentro de la hiperesfera multiplica el volumen del hipercubo para estimar el volumen de la hiperesfera.

### Eficiencia en Altas Dimensiones
La simulación de Monte Carlo se vuelve menos eficiente en dimensiones altas debido a la **maldición de la dimensionalidad**: el volumen de la hiperesfera se concentra cerca de su superficie, y la fracción de puntos generados dentro de ella disminuye exponencialmente con el número de dimensiones. Esto requiere un número de muestras extremadamente grande para obtener una estimación precisa.

## Errores y Soluciones
- **Error inicial**: Usar `math.gamma` en lugar de `scipy.special.gamma` para valores no enteros.
  - **Solución**: Usar `scipy.special.gamma` que maneja correctamente valores reales.
- **Error de cálculo del volumen del hipercubo**: Usar \( (2R)^n \) correctamente.
  - **Solución**: Verificar que el lado del hipercubo es \( 2R = 4 \), por lo tanto, el volumen es \( 4^{10} \).

## Resultado
El código ejecuta ambos métodos, compara los resultados y muestra la diferencia. El error relativo es pequeño, demostrando que Monte Carlo es efectivo incluso en 10 dimensiones, aunque su eficiencia disminuye con más dimensiones.

Este archivo documenta la lógica implementada y los errores encontrados.