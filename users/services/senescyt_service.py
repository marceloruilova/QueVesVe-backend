"""
Servicio de verificación de títulos profesionales contra el registro
público SENESCYT Ecuador (SNIESE).

El portal SENESCYT usa un formulario JSF en:
https://sniese.senescyt.gob.ec/siies-web/paginas/consulta-publica/queryTitulosByParams.jsf

Se consulta via HTTP pasando la cédula y/o número de registro.
Si el servicio externo falla, retorna verified=False con error explicativo.
"""

import logging
from typing import TypedDict

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SENESCYT_TIMEOUT = 15
SENESCYT_SEARCH_URL = (
    "https://sniese.senescyt.gob.ec/siies-web/paginas/consulta-publica/"
    "queryTitulosByParams.jsf"
)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; QueVesVe/1.0; +https://quevesve.com)"
    ),
    "Accept": "text/html,application/xhtml+xml",
}


class SenescytResult(TypedDict):
    verified: bool
    name: str
    title: str
    institution: str
    error: str


def verify_senescyt(cedula: str, senescyt_number: str) -> SenescytResult:
    """
    Verifica si el número de registro SENESCYT existe y corresponde
    a la cédula proporcionada.

    Returns SenescytResult con verified=True y los datos del titular
    si la verificación es exitosa, o verified=False con el campo error
    explicando la razón del fallo.
    """
    result: SenescytResult = {
        "verified": False,
        "name": "",
        "title": "",
        "institution": "",
        "error": "",
    }

    try:
        session = requests.Session()
        session.headers.update(HEADERS)

        # Primera solicitud para obtener el ViewState JSF
        init_resp = session.get(SENESCYT_SEARCH_URL, timeout=SENESCYT_TIMEOUT)
        init_resp.raise_for_status()

        soup = BeautifulSoup(init_resp.text, "html.parser")
        viewstate_tag = soup.find("input", {"name": "javax.faces.ViewState"})
        if not viewstate_tag:
            logger.warning("SENESCYT: no se encontró ViewState en la página")
            result["error"] = "SENESCYT_PARSE_ERROR"
            return result

        viewstate = viewstate_tag.get("value", "")

        # Segunda solicitud: envío del formulario de búsqueda por número de registro
        form_data = {
            "javax.faces.ViewState": viewstate,
            "javax.faces.partial.ajax": "true",
            "javax.faces.partial.execute": "@all",
            "javax.faces.partial.render": "@all",
            "numRegistro": senescyt_number,
            "cedula": cedula,
        }

        search_resp = session.post(
            SENESCYT_SEARCH_URL,
            data=form_data,
            timeout=SENESCYT_TIMEOUT,
        )
        search_resp.raise_for_status()

        result_soup = BeautifulSoup(search_resp.text, "html.parser")

        # El portal SENESCYT devuelve una tabla con los datos del titular.
        # Se busca el nombre, título e institución en las celdas de la tabla.
        rows = result_soup.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 3:
                # Formato típico: Nombre | Título | Institución | Nro. Registro
                candidate_name = cells[0].get_text(strip=True)
                candidate_title = cells[1].get_text(strip=True)
                candidate_institution = cells[2].get_text(strip=True)

                # Verificar que el número de registro aparece en la fila
                row_text = row.get_text()
                if senescyt_number in row_text and candidate_name:
                    result["verified"] = True
                    result["name"] = candidate_name
                    result["title"] = candidate_title
                    result["institution"] = candidate_institution
                    return result

        # Si no se encontró ninguna fila coincidente
        result["error"] = "SENESCYT_NOT_FOUND"

    except requests.Timeout:
        logger.error("SENESCYT: timeout al consultar el servicio")
        result["error"] = "SENESCYT_TIMEOUT"
    except requests.ConnectionError:
        logger.error("SENESCYT: error de conexión al servicio")
        result["error"] = "SENESCYT_UNAVAILABLE"
    except requests.HTTPError as exc:
        logger.error("SENESCYT: error HTTP %s", exc)
        result["error"] = "SENESCYT_HTTP_ERROR"
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("SENESCYT: error inesperado: %s", exc)
        result["error"] = "SENESCYT_UNKNOWN_ERROR"

    return result
