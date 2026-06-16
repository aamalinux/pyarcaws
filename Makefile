all: .venv install test

.venv:
	virtualenv -p python3 .venv
	.venv/bin/pip install -r requirements.txt
	.venv/bin/pip install -r requirements-dev.txt

install:
	.venv/bin/python setup.py install

test:
	.venv/bin/py.test tests

clean:
	rm -Rf .venv

# Copia las plantillas de configuración (.ini) de conf/ al directorio actual.
# El certificado/clave de prueba ya NO se descargan: el reingart.zip del upstream
# está vencido (404). Para obtener un certificado de homologación, generarlo por
# autogestión WSASS (ver README, sección "Certificado").
get-auth:
	cp conf/*.ini .
	@echo "Genera tu certificado de homologacion por WSASS (ver README)."

access-ticket:
	python -m pyarcaws.wsaa

sample-invoice:
	python -m pyarcaws.wsfev1 --prueba

# Use "git clean -n" to see the files to be cleaned
# Use only when only the config files are untracked
# Finally use "git clean -f" to remove untracked files(in this case test files)
# This command will list all the files that are untracked. You can clean them verbosely
# using git clean -i. Else, if you are sure, you can se -f to remove all untracked files
# without a prompt
clean-test:
	git clean -n
	git clean -i

.PHONY: install test get-auth sample-invoice sign-cert
