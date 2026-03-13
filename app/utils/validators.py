"""
Modulo de validadores para datos de entrada
Valida emails, NIFs/CIFs, telefonos, etc. segun estandares españoles
"""
import re
from typing import Union


class Validators:
    """Validadores centralizados para datos de entrada"""

    @staticmethod
    def validar_email(email: str | None) -> tuple[bool, str]:
        """
        Valida formato de email.

        Args:
            email (str): Email a validar

        Returns:
            tuple: (bool valido, str mensaje_error)
        """
        if not email or not email.strip():
            return True, ""  # Email vacio es valido (campo opcional)

        email = email.strip().lower()

        # Patron basico de email (RFC 5322 simplificado)
        patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        if not re.match(patron, email):
            return False, "Formato de email invalido. Ejemplo: usuario@ejemplo.com"

        # Validaciones adicionales
        if len(email) > 254:  # RFC 5321
            return False, "Email demasiado largo (maximo 254 caracteres)"

        partes = email.split('@')
        if len(partes[0]) > 64:  # RFC 5321
            return False, "Parte local del email demasiado larga (maximo 64 caracteres)"

        return True, ""

    @staticmethod
    def validar_nif_cif_nie(documento: str | None) -> tuple[bool, str]:
        """
        Valida NIF, CIF o NIE español con algoritmo oficial.

        Formatos aceptados:
        - NIF: 12345678Z (8 digitos + letra)
        - NIE: X1234567Z (X/Y/Z + 7 digitos + letra)
        - CIF: A12345678 (letra + 8 digitos/letra)

        Args:
            documento (str): NIF/CIF/NIE a validar

        Returns:
            tuple: (bool valido, str mensaje_error)
        """
        if not documento or not documento.strip():
            return True, ""  # Documento vacio es valido (campo opcional)

        doc = documento.strip().upper().replace(' ', '').replace('-', '')

        # Validar DNI/NIF (8 digitos + letra)
        if re.match(r'^\d{8}[A-Z]$', doc):
            return Validators._validar_dni(doc)

        # Validar NIE (X/Y/Z + 7 digitos + letra)
        if re.match(r'^[XYZ]\d{7}[A-Z]$', doc):
            return Validators._validar_nie(doc)

        # Validar CIF (letra + 7 digitos + digito/letra)
        if re.match(r'^[A-HJ-NP-SUVW]\d{7}[0-9A-J]$', doc):
            return Validators._validar_cif(doc)

        return False, "Formato invalido. Debe ser NIF (12345678Z), NIE (X1234567Z) o CIF (A12345678)"

    @staticmethod
    def _validar_dni(dni: str) -> tuple[bool, str]:
        """Valida DNI con letra de control"""
        numero = int(dni[:8])
        letra = dni[8]
        letras = "TRWAGMYFPDXBNJZSQVHLCKE"
        letra_correcta = letras[numero % 23]

        if letra != letra_correcta:
            return False, f"Letra de control incorrecta. Deberia ser {letra_correcta}"

        return True, ""

    @staticmethod
    def _validar_nie(nie: str) -> tuple[bool, str]:
        """Valida NIE con letra de control"""
        # Reemplazar primera letra por numero
        reemplazos = {'X': '0', 'Y': '1', 'Z': '2'}
        numero_str = reemplazos[nie[0]] + nie[1:8]
        numero = int(numero_str)

        letra = nie[8]
        letras = "TRWAGMYFPDXBNJZSQVHLCKE"
        letra_correcta = letras[numero % 23]

        if letra != letra_correcta:
            return False, f"Letra de control incorrecta. Deberia ser {letra_correcta}"

        return True, ""

    @staticmethod
    def _validar_cif(cif: str) -> tuple[bool, str]:
        """Valida CIF con digito/letra de control"""
        # Algoritmo oficial de validacion de CIF
        tipo_org = cif[0]
        numeros = cif[1:8]
        control = cif[8]

        # Calcular suma de digitos pares
        suma_pares = sum(int(numeros[i]) for i in range(1, 7, 2))

        # Calcular suma de digitos impares (con regla especial)
        suma_impares = 0
        for i in range(0, 7, 2):
            doble = int(numeros[i]) * 2
            suma_impares += doble // 10 + doble % 10

        suma_total = suma_pares + suma_impares
        unidad = suma_total % 10
        digito_control = (10 - unidad) % 10

        # Algunas organizaciones usan letra en lugar de digito
        letras_control = "JABCDEFGHI"
        letra_control = letras_control[digito_control]

        # Organizaciones que DEBEN usar letra
        usa_letra = tipo_org in 'NPQRSW'
        # Organizaciones que PUEDEN usar letra o digito
        puede_letra = tipo_org in 'ABEH'

        if usa_letra:
            if control != letra_control:
                return False, f"Letra de control incorrecta. Deberia ser {letra_control}"
        elif puede_letra:
            if control != str(digito_control) and control != letra_control:
                return False, f"Control incorrecto. Deberia ser {digito_control} o {letra_control}"
        else:
            if control != str(digito_control):
                return False, f"Digito de control incorrecto. Deberia ser {digito_control}"

        return True, ""

    @staticmethod
    def validar_telefono(telefono: str | None) -> tuple[bool, str]:
        """
        Valida numero de telefono español.

        Formatos aceptados:
        - Movil: 612345678, +34612345678, 0034612345678
        - Fijo: 912345678, +34912345678

        Args:
            telefono (str): Telefono a validar

        Returns:
            tuple: (bool valido, str mensaje_error)
        """
        if not telefono or not telefono.strip():
            return True, ""  # Telefono vacio es valido (campo opcional)

        tel = telefono.strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')

        # Eliminar prefijos internacionales
        if tel.startswith('+34'):
            tel = tel[3:]
        elif tel.startswith('0034'):
            tel = tel[4:]
        elif tel.startswith('34') and len(tel) == 11:
            tel = tel[2:]

        # Validar formato español (9 digitos empezando por 6, 7, 8, 9)
        if not re.match(r'^[6789]\d{8}$', tel):
            return False, "Telefono invalido. Debe tener 9 digitos y empezar por 6, 7, 8 o 9"

        return True, ""

    @staticmethod
    def validar_codigo_postal(cp: str | None) -> tuple[bool, str]:
        """
        Valida codigo postal español (5 digitos).

        Args:
            cp (str): Codigo postal a validar

        Returns:
            tuple: (bool valido, str mensaje_error)
        """
        if not cp or not cp.strip():
            return True, ""  # CP vacio es valido (campo opcional)

        cp = cp.strip()

        if not re.match(r'^\d{5}$', cp):
            return False, "Codigo postal invalido. Debe tener 5 digitos (ej: 28001)"

        # Validar rango (01000 a 52999)
        cp_num = int(cp)
        if cp_num < 1000 or cp_num > 52999:
            return False, "Codigo postal fuera de rango valido (01000-52999)"

        return True, ""

    @staticmethod
    def validar_imei(imei: str | None) -> tuple[bool, str]:
        """
        Valida codigo IMEI de dispositivo movil (algoritmo Luhn).

        Args:
            imei (str): IMEI a validar (15 digitos)

        Returns:
            tuple: (bool valido, str mensaje_error)
        """
        if not imei or not imei.strip():
            return True, ""  # IMEI vacio es valido (campo opcional)

        imei = imei.strip().replace(' ', '').replace('-', '')

        # IMEI debe tener 15 digitos
        if not re.match(r'^\d{15}$', imei):
            return False, "IMEI invalido. Debe tener 15 digitos"

        # Algoritmo de Luhn para validar IMEI
        suma = 0
        alternar = False

        for i in range(len(imei) - 1, -1, -1):
            digito = int(imei[i])

            if alternar:
                digito *= 2
                if digito > 9:
                    digito -= 9

            suma += digito
            alternar = not alternar

        if suma % 10 != 0:
            return False, "IMEI invalido (fallo verificacion Luhn)"

        return True, ""

    @staticmethod
    def validar_precio(
        precio: Union[float, int, str],
        min_valor: float = 0,
        max_valor: float = 999999.99
    ) -> tuple[bool, str]:
        """
        Valida que un precio sea valido.

        Args:
            precio: Precio a validar (float, int o str)
            min_valor: Valor minimo permitido
            max_valor: Valor maximo permitido

        Returns:
            tuple: (bool valido, str mensaje_error)
        """
        try:
            if isinstance(precio, str):
                precio = float(precio.replace(',', '.'))
            else:
                precio = float(precio)

            if precio < min_valor:
                return False, f"Precio debe ser mayor o igual a {min_valor}"

            if precio > max_valor:
                return False, f"Precio debe ser menor o igual a {max_valor}"

            # Validar que no tenga mas de 2 decimales
            if round(precio, 2) != precio:
                return False, "Precio no puede tener mas de 2 decimales"

            return True, ""

        except (ValueError, TypeError):
            return False, "Precio invalido. Debe ser un numero"

    @staticmethod
    def validar_cantidad(
        cantidad: Union[int, str],
        min_valor: int = 1,
        max_valor: int = 99999
    ) -> tuple[bool, str]:
        """
        Valida que una cantidad sea valida.

        Args:
            cantidad: Cantidad a validar (int o str)
            min_valor: Valor minimo permitido
            max_valor: Valor maximo permitido

        Returns:
            tuple: (bool valido, str mensaje_error)
        """
        try:
            cantidad = int(cantidad)

            if cantidad < min_valor:
                return False, f"Cantidad debe ser mayor o igual a {min_valor}"

            if cantidad > max_valor:
                return False, f"Cantidad debe ser menor o igual a {max_valor}"

            return True, ""

        except (ValueError, TypeError):
            return False, "Cantidad invalida. Debe ser un numero entero"
