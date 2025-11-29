# Análisis y Solución del Método de Monte Carlo para Estimar π

## Objetivo
Crear un programa en Python que estime el valor de π utilizando el método de Monte Carlo, generando 1,000,000 de puntos aleatorios en un plano 2D y determinando cuántos caen dentro de un círculo unitario. Luego, calcular π basado en la proporción y comparar con el valor real `math.pi`, mostrando el porcentaje de error.

## Implementación

### Paso 1: Generación de puntos aleatorios
Se utilizó `numpy.random.uniform(-1, 1, (num_points, 2))` para generar 1,000,000 puntos en el cuadrado unitario `[-1, 1] × [-1, 1]`. Esta operación se vectoriza con NumPy para mejorar el rendimiento.

### Paso 2: Cálculo de distancias al origen
Se calculó el cuadrado de la distancia al origen para cada punto usando `np.sum(points**2, axis=1)`, lo cual es más eficiente que un bucle tradicional.

### Paso 3: Conteo de puntos dentro del círculo
Se determinó cuántos puntos cumplen con la condición `distancia² ≤ 1` usando un array booleano `inside_circle = distances_squared <= 1`, y se contó con `np.sum(inside_circle)`.

### Paso 4: Estimación de π
La estimación se realizó como:
```
π ≈ (número de puntos dentro del círculo / total de puntos) × 4
```
ya que el área del círculo unitario es π y el área del cuadrado es 4.

### Paso 5: Comparación y error
Se comparó el resultado con `math.pi` y se calculó el porcentaje de error:
```
error% = |(estimación - valor real)| / valor real × 100
```

## Problema encontrado y solución

### Error: `UnicodeEncodeError: 'charmap' codec can't encode character '\\u03c0'`
Al ejecutar el programa inicialmente, se produjo un error de codificación al intentar imprimir el símbolo π (`\\u03c0`) en la salida, específicamente en el sistema operativo Windows con la codificación predeterminada `cp1252`, que no soporta ciertos caracteres Unicode.

#### Solución
Reemplacé el uso del símbolo `π` en las cadenas de impresión por su representación textual "pi" para evitar el problema de codificación. Por ejemplo:
- Antes: `print(f"Estimación de π: {estimated_pi}")`
- Después: `print(f"Estimación de pi: {estimated_pi}")`

Este cambio garantiza que el programa funcione correctamente en entornos con codificación limitada como `cp1252`, sin perder claridad ni funcionalidad.

## Resultados
- Número de puntos generados: 1,000,000
- Puntos dentro del círculo: 785,471
- Estimación de pi: 3.141884
- Valor real de pi: 3.141592653589793
- Porcentaje de error: 0.009274%

## Conclusión
El método de Monte Carlo demostró ser efectivo para estimar π con alta precisión. La implementación con NumPy fue rápida y eficiente, y la solución al problema de codificación aseguró que el programa sea portable y funcional en diferentes entornos.

El archivo `monte_carlo_pi.py` ha sido creado y ejecutado correctamente, y el análisis se ha documentado en este archivo.