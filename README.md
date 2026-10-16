# FHIR Lite

FHIR Lite es una libreria de Python ultra ligera y sin dependencias externas diseñada para manejar, modificar y convertir recursos medicos bajo el estandar **FHIR (Fast Healthcare Interoperability Resources)**. 

Esta construida especificamente para entornos donde la velocidad y el tamaño del paquete son criticos (como AWS Lambda, GCP Cloud Run o Dataflow), permitiendo una interoperabilidad fluida entre sistemas modernos (JSON) y sistemas medicos heredados / legacy (XML).

## 鉁� Caracteristicas

* **Cero Dependencias:** Utiliza exclusivamente las bibliotecas estandar de Python (`json` y `xml.etree.ElementTree`). No requiere `pip install`.
* **Serverless-Friendly:** Pesa solo unos pocos kilobytes, ideal para arquitecturas de microservicios orientadas a eventos.
* **Conversion Bidireccional:** Transforma facilmente recursos de FHIR JSON a FHIR XML y viceversa.
* **Facil de Extender:** Arquitectura orientada a objetos que permite heredar y crear validadores de recursos especificos (ej. `Patient`, `Observation`).