import requests

token = "TOKEN_GOES_HERE"

url = "https://certificationapi.oshwa.org/api/projects"

responsiblePartyType = "Company"
responsibleParty = "Adafruit Industries, LLC"
bindingParty = "Limor Fried"
country = "United States of America"
streetAddress1 = "150 Varick St."
streetAddress2 = ""
city = "New York"
state = "New York"
postalCode = "10013"
privateContact = "oshw@adafruit.com"
publicContact = "oshw@adafruit.com"
projectName = "Adafruit QT Py = SAMD21 Dev Board with STEMMA QT"
projectWebsite = "https://www.adafruit.com/product/4600"
projectVersion = "Rev C"
previousVersions = "[]"
projectDescription = "This diminutive dev board comes with our favorite lil chip, the SAMD21. OLEDs! Inertial Measurement Units! Sensors a-plenty. All plug-and-play thanks to the innovative chainable design: SparkFun Qwiic-compatible STEMMA QT connectors for the I2C bus so you don't even need to solder. It also has 11 GPIO pins and a built-in NeoPixel RGB LED. This board ships with CircuitPython but also works great with Arduino." #pylint: disable=line-too-long
primaryType = "Electronics"
additionalType = '[ "Electronics"]'
projectKeywords = f'[ "{projectName}", "CircuitPython"]'
documentationUrl = "https://learn.adafruit.com/adafruit-qt-py"
hardwareLicense = "Other"
softwareLicense = "MIT"
documentationLicense = "CC BY-SA"
relationship = "PROJECT IS DESIGNED AND DISTRIBUTED BY ADAFRUIT INDUSTRIES"

payload = f'{{"responsiblePartyType": "{responsiblePartyType}","responsibleParty": "{responsibleParty}","bindingParty": "{bindingParty}","country": "{country}","streetAddress1": "{streetAddress1}","streetAddress2": "{streetAddress1}","city": "{city}","state": "{state}","postalCode": "{postalCode}","privateContact": "{privateContact}","publicContact": "{publicContact}","projectName": "{projectName}","projectWebsite": "{projectWebsite}","projectVersion": "{projectVersion}","previousVersions": {previousVersions},"projectDescription": "{projectDescription}","primaryType": "{primaryType}","additionalType": {additionalType},"projectKeywords": {projectKeywords},"citations": [{{}}],"documentationUrl": "{documentationUrl}","availableFileFormat": true,"hardwareLicense": "{hardwareLicense}","softwareLicense": "{softwareLicense}","documentationLicense": "{documentationLicense}","noCommercialRestriction": true,"noDocumentationRestriction": true,"openHardwareComponents": "true","creatorContribution": true,"noUseRestriction": true,"redistributedWork": true,"noSpecificProduct": "true","noComponentRestriction": true,"technologyNeutral": true,"certificationMarkTerms": {{ "accurateContactInformation": {{ "term": "I have provided OSHWA with accurate contact information, recognize that all official communications from OSHWA will be directed to that contact information, and will update that contact information as necessary.", "agreement": true }}}},"explanationCertificationTerms": "N/A (I agree to all terms)","relationship": "{relationship}","agreementTerms": true,"parentName": ""}}' #pylint: disable=line-too-long
print(payload)

headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}

r = requests.request("POST", url, headers=headers, data=payload)

print("\n")
print(r.status_code)
print("\n")
print(r.json())
