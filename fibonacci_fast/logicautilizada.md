El archivo `ejecicio.md` indica que se debe calcular el 500,000-ésimo número de Fibonacci utilizando un algoritmo eficiente como la Exponenciación de Matrices o Fast Doubling, con complejidad O(log n), para evitar tiempos de ejecución excesivos. Dado que el número será muy grande, solo se deben imprimir los últimos 100 dígitos.

Para cumplir con esta tarea, se implementó el algoritmo de **Fast Doubling**, que permite calcular el n-ésimo número de Fibonacci en O(log n) tiempo mediante una recursión eficiente basada en identidades matemáticas:

- F(2k) = F(k) * [2*F(k+1) - F(k)]
- F(2k+1) = F(k+1)^2 + F(k)^2

Este método es más eficiente que la exponenciación de matrices en términos de constantes y evita el uso de operaciones matriciales complejas.

Se implementó una función recursiva con memoización (usando un diccionario) para evitar cálculos redundantes, aunque el número de llamadas recursivas es logarítmico en n. Dado que n = 500,000, el número de llamadas es muy pequeño.

Además, se usó la función `pow` con módulo para calcular solo los últimos 100 dígitos, pero dado que se necesita el valor completo (para poder extraer los últimos 100 dígitos), se realiza el cálculo sin módulo en el proceso, pero se almacena el número completo como entero. Sin embargo, para evitar el uso excesivo de memoria, se hace uso de la propiedad de que solo se necesitan los últimos 100 dígitos, por lo que se puede realizar el cálculo en módulo 10^100. Esto se hace porque:

- (a + b) mod m = (a mod m + b mod m) mod m
- (a * b) mod m = (a mod m * b mod m) mod m

Por lo tanto, se realiza todo el cálculo módulo 10^100, lo cual reduce el tamaño de los números a manejar.

Se implementó el algoritmo de Fast Doubling con módulo 10^100.

Error detectado inicialmente: Se intentó usar `numpy` para operaciones matriciales, pero se indicó que no se debe ejecutar `pip show numpy`, y además, no se necesita `numpy` para este algoritmo. Se decidió no usar `numpy` para mantener la simplicidad y evitar dependencias innecesarias.

Solución: Se implementó el algoritmo directamente en Python sin dependencias externas.

El script se guardó en `fibonacci_fast_doubling.py` y se generó el archivo `logicautilizada.md` con la explicación de la lógica, errores y soluciones.

Se verificó que el resultado sea solo los últimos 100 dígitos, como se requiere.