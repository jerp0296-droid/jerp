import sys
import requests
from datetime import datetime, timezone, timedelta
from xml.etree.ElementTree import Element, SubElement, ElementTree, tostring
from xml.dom import minidom


# ============================================================
# CONFIGURACIÓN
# ============================================================

CANALES = {
    "entfamily.cl": {
        "nombre": "ENT Family",
        "url": "https://api.40mediagroup.com/xmltv/programacion/entfamily/guia.json",
    },

    "entchannel.cl": {
        "nombre": "ENT Channel",
        "url": "https://api.40mediagroup.com/xmltv/programacion/entchannel/guia.json",
    },
}

OUTPUT = "XLGFHD.xml"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}


# ============================================================
# DESCARGAR JSON
# ============================================================

def descargar_json(url):
    respuesta = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    respuesta.raise_for_status()

    return respuesta.json()


# ============================================================
# CONVERTIR HORA A COLOMBIA
# ============================================================

def fmt_xmltv(fecha):
    """
    Convierte una fecha ISO de la API de 40 Media
    a formato XMLTV usando hora de Colombia.

    Ejemplo:

    2026-09-30T18:01:48+00:00

    se convierte en:

    20260930130148 -0500
    """

    dt = datetime.fromisoformat(fecha)

    # Si la fecha no trae zona horaria,
    # asumimos que está en UTC.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    # Colombia UTC-5
    colombia = timezone(timedelta(hours=-5))

    dt = dt.astimezone(colombia)

    return dt.strftime("%Y%m%d%H%M%S -0500")


# ============================================================
# LIMPIAR TEXTO
# ============================================================

def texto(valor):
    if valor is None:
        return ""

    return str(valor).strip()


# ============================================================
# CONSTRUIR XMLTV
# ============================================================

def construir_xml(datos_por_canal):

    tv = Element(
        "tv",
        {
            "generator-info-name": "40media-EPG",
            "generator-info-url": "https://www.40mediagroup.com",
        }
    )

    # --------------------------------------------------------
    # CANALES
    # --------------------------------------------------------

    for cid, info in CANALES.items():

        canal = SubElement(
            tv,
            "channel",
            {
                "id": cid
            }
        )

        SubElement(
            canal,
            "display-name",
            {
                "lang": "es"
            }
        ).text = info["nombre"]

    # --------------------------------------------------------
    # PROGRAMACIÓN
    # --------------------------------------------------------

    for cid, data in datos_por_canal.items():

        programas = data.get("programmes", [])

        # Ordenar por fecha de inicio
        programas = sorted(
            programas,
            key=lambda x: x.get("start", "")
        )

        vistos = set()

        for p in programas:

            start = texto(p.get("start"))
            stop = texto(p.get("stop"))
            title = texto(p.get("title"))

            # Ignorar programas incompletos
            if not start or not stop or not title:
                continue

            # Evitar duplicados
            clave = (
                cid,
                start,
                stop,
                title
            )

            if clave in vistos:
                continue

            vistos.add(clave)

            # ------------------------------------------------
            # PROGRAMA
            # ------------------------------------------------

            prog = SubElement(
                tv,
                "programme",
                {
                    "start": fmt_xmltv(start),
                    "stop": fmt_xmltv(stop),
                    "channel": cid,
                }
            )

            # TÍTULO
            SubElement(
                prog,
                "title",
                {
                    "lang": "es"
                }
            ).text = title

            # SUBTÍTULO
            subtitle = texto(
                p.get("subtitle")
            )

            if subtitle:

                SubElement(
                    prog,
                    "sub-title",
                    {
                        "lang": "es"
                    }
                ).text = subtitle

            # DESCRIPCIÓN
            descripcion = texto(
                p.get("desc")
            )

            if descripcion:

                SubElement(
                    prog,
                    "desc",
                    {
                        "lang": "es"
                    }
                ).text = descripcion

            # CATEGORÍA
            categoria = texto(
                p.get("category")
            )

            if categoria:

                SubElement(
                    prog,
                    "category",
                    {
                        "lang": "es"
                    }
                ).text = categoria

            # ICONO
            icono = texto(
                p.get("icon")
            )

            if icono:

                SubElement(
                    prog,
                    "icon",
                    {
                        "src": icono
                    }
                )

    return ElementTree(tv)


# ============================================================
# GUARDAR XML
# ============================================================

def guardar_xml(tree, archivo):

    xml_bytes = tostring(
        tree.getroot(),
        encoding="utf-8"
    )

    bonito = minidom.parseString(
        xml_bytes
    ).toprettyxml(
        indent="  ",
        encoding="UTF-8"
    )

    with open(
        archivo,
        "wb"
    ) as f:

        f.write(bonito)


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():

    datos = {}

    print("==========================================")
    print("       GENERADOR XMLTV 40 MEDIA")
    print("==========================================")

    for cid, info in CANALES.items():

        print()
        print(
            f"[+] Descargando {info['nombre']}..."
        )

        try:

            data = descargar_json(
                info["url"]
            )

            programas = data.get(
                "programmes",
                []
            )

            print(
                f"    OK: {len(programas)} programas"
            )

            datos[cid] = data

        except Exception as e:

            print(
                f"    ERROR: {e}",
                file=sys.stderr
            )

            datos[cid] = {
                "programmes": []
            }

    print()
    print("[+] Generando guia.xml...")

    tree = construir_xml(
        datos
    )

    guardar_xml(
        tree,
        OUTPUT
    )

    print()
    print("==========================================")
    print("[OK] guia.xml generado correctamente")
    print("==========================================")


if __name__ == "__main__":
    main()
