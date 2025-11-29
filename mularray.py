from functools import wraps
import sys
import time
import numpy as np

def multiply_arrays_numpy(arr1, arr2):
    # Convertir las listas a arrays de NumPy
    arr1_np = np.array(arr1)
    arr2_np = np.array(arr2)
    
    # Realizar la multiplicación elemento a elemento
    result = arr1_np * arr2_np
    
    # Convertir el resultado a una lista
    return result.tolist()

def multiply_arrays(arr1, arr2):
    return [a * b for a, b in zip(arr1, arr2)]

def measure_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"{func.__name__} ejecutada en {end_time - start_time:.4f} segundos")
        return result
    return wrapper


#Ejemplo de uso 
if __name__ == "__main__":
    # si hay agumentos los tomas
    if len(sys.argv) == 3:
        array1 = [int(sys.argv[1])]
        array2 = [int(sys.argv[2])]
    else:
        array1 = [1, 2, 3]
        array2 = [4, 5, 6]
    
    
result1 = multiply_arrays_numpy(array1, array2)
result2 = multiply_arrays(array1, array2)
print("Resultado con NumPy:", result1)
print("Resultado sin NumPy:", result2)


    
