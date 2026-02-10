"""
Utilidades para optimizar la carga de datos en QTableWidget
Soluciona el problema de performance con setRowCount(0) + insertRow loops
"""
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem
from PyQt5.QtCore import Qt


class TableOptimizer:
    """Optimiza la carga de datos en tablas Qt"""

    @staticmethod
    def cargar_datos_optimizado(tabla, datos, config_columnas):
        """
        Carga datos en una tabla de forma optimizada.

        PROBLEMA ANTERIOR:
        - setRowCount(0)  # Borra todo
        - for each row:
        -     insertRow()  # Inserta fila por fila (LENTO)

        SOLUCIÓN NUEVA:
        - setRowCount(len(datos))  # Preasigna todas las filas de una vez
        - for each row:
        -     setItem()  # Solo establece los items (RÁPIDO)

        Args:
            tabla (QTableWidget): La tabla a llenar
            datos (list): Lista de diccionarios con los datos
            config_columnas (list): Configuración de columnas
                Formato: [
                    {'key': 'nombre', 'col': 0, 'alignment': Qt.AlignLeft},
                    {'key': 'precio', 'col': 1, 'alignment': Qt.AlignRight, 'format': lambda x: f"{x:.2f} €"},
                    ...
                ]

        Returns:
            int: Número de filas cargadas
        """
        # Deshabilitar updates durante la carga (MÁS RÁPIDO)
        tabla.setUpdatesEnabled(False)

        try:
            # Establecer número de filas DE UNA VEZ (evita insertRow repetido)
            num_filas = len(datos)
            tabla.setRowCount(num_filas)

            # Llenar datos
            for row_idx, registro in enumerate(datos):
                # Establecer altura de fila si es necesario
                # tabla.setRowHeight(row_idx, 60)  # Descomentar si necesitas altura fija

                for config in config_columnas:
                    key = config['key']
                    col = config['col']
                    valor = registro.get(key, '')

                    # Aplicar formato si existe
                    if 'format' in config and callable(config['format']):
                        valor_texto = config['format'](valor)
                    else:
                        valor_texto = str(valor) if valor is not None else ''

                    # Crear item
                    item = QTableWidgetItem(valor_texto)

                    # Aplicar alineación si existe
                    if 'alignment' in config:
                        item.setTextAlignment(config['alignment'])

                    # Aplicar color de texto si existe
                    if 'text_color' in config and callable(config['text_color']):
                        color = config['text_color'](valor)
                        if color:
                            item.setForeground(color)

                    # Establecer item
                    tabla.setItem(row_idx, col, item)

                # Guardar datos completos del registro en la fila (útil para botones)
                # Se puede acceder con: tabla.item(row, 0).data(Qt.UserRole)
                if config_columnas:
                    primer_item = tabla.item(row_idx, config_columnas[0]['col'])
                    if primer_item:
                        primer_item.setData(Qt.UserRole, registro)

            return num_filas

        finally:
            # Reactivar updates
            tabla.setUpdatesEnabled(True)

    @staticmethod
    def cargar_datos_paginado(tabla, datos, config_columnas, pagina=1, por_pagina=100):
        """
        Carga datos con paginación.

        Args:
            tabla (QTableWidget): La tabla a llenar
            datos (list): Lista COMPLETA de datos
            config_columnas (list): Configuración de columnas
            pagina (int): Número de página (1-based)
            por_pagina (int): Registros por página

        Returns:
            dict: {
                'cargados': int,  # Registros cargados
                'total': int,     # Total de registros
                'pagina': int,    # Página actual
                'total_paginas': int  # Total de páginas
            }
        """
        total = len(datos)
        total_paginas = (total + por_pagina - 1) // por_pagina  # Redondeo hacia arriba

        # Calcular rango de datos para esta página
        inicio = (pagina - 1) * por_pagina
        fin = min(inicio + por_pagina, total)

        # Obtener datos de la página actual
        datos_pagina = datos[inicio:fin]

        # Cargar datos optimizado
        cargados = TableOptimizer.cargar_datos_optimizado(tabla, datos_pagina, config_columnas)

        return {
            'cargados': cargados,
            'total': total,
            'pagina': pagina,
            'total_paginas': total_paginas
        }

    @staticmethod
    def crear_item_numerico(valor, decimales=2, sufijo=''):
        """
        Crea un item de tabla para valores numéricos con formato y alineación correcta.

        Args:
            valor: Valor numérico
            decimales (int): Decimales a mostrar
            sufijo (str): Sufijo (ej: ' €', '%')

        Returns:
            QTableWidgetItem: Item configurado
        """
        if valor is None:
            valor = 0

        texto = f"{float(valor):.{decimales}f}{sufijo}"
        item = QTableWidgetItem(texto)
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return item

    @staticmethod
    def crear_item_centrado(texto):
        """
        Crea un item de tabla centrado.

        Args:
            texto (str): Texto a mostrar

        Returns:
            QTableWidgetItem: Item configurado
        """
        item = QTableWidgetItem(str(texto) if texto else '')
        item.setTextAlignment(Qt.AlignCenter)
        return item


# EJEMPLO DE USO:
#
# from app.ui.table_optimizer import TableOptimizer
#
# # Configuración de columnas
# config = [
#     {'key': 'codigo_ean', 'col': 0, 'alignment': Qt.AlignCenter},
#     {'key': 'descripcion', 'col': 1},
#     {'key': 'precio', 'col': 2, 'alignment': Qt.AlignRight,
#      'format': lambda x: f"{x:.2f} €"},
#     {'key': 'stock', 'col': 3, 'alignment': Qt.AlignCenter,
#      'text_color': lambda x: Qt.red if x == 0 else None}
# ]
#
# # Cargar datos (RÁPIDO)
# productos = self.producto_manager.buscar_productos()
# TableOptimizer.cargar_datos_optimizado(self.tabla, productos, config)
#
# # O con paginación
# info = TableOptimizer.cargar_datos_paginado(
#     self.tabla, productos, config, pagina=1, por_pagina=50
# )
# print(f"Mostrando {info['cargados']} de {info['total']} productos")
