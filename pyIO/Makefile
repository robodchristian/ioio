NAME = pyIO
TARDIR = ~/Downloads
PREFIX = /usr/local
INSTALL = install
PYTHON ?= python
PYTHON-COVERAGE ?= python-coverage
TESTS ?= tests/*.py

.PHONY: all tar tarall check check-py check-sh
#.PHONY: install install-bin install-man
.PHONY: coverage report annotate clean pychecker

all:	pin_map.py

pin_map.py:	buildmap.py pins.txt
	./buildmap.py pins.txt pin_map.py

# Install on system (run under sudo)
#install:	

#install-bin:
#	$(INSTALL) -v -m 755 pyIO $(PREFIX)/bin/

#install-man:
#	$(INSTALL) -v -m 644 pyIO.1 $(PREFIX)/share/man/man1/

# Build tarball for distribution
tar:
	eval `grep '^VERSION' pyIO.py`; VERSION=`echo $$VERSION | cut -c5-99` ; echo $$VERSION ; \
	(cd .. && ln -s $(NAME) $(NAME)-$$VERSION ; \
	  tar czf $(TARDIR)/$(NAME)-$$VERSION.tgz --exclude-backups \
	  $(NAME)-$$VERSION/*.{py,txt} \
	  $(NAME)-$$VERSION/Makefile $(NAME)-$$VERSION/tests/*test.py \
	    && status=true || status=false; \
	  [ -L $(NAME)-$$VERSION ] && rm -f $(NAME)-$$VERSION) ; $$status

# Run all tests
# NOTE: you have to have access to an IOIO to run the tests.
# Specify the IOIO BlueTooth address in the IOIO environment variable:
#   IOIO='00:1F:81:00:08:30' make coverage report annotate
check:	check-py #check-sh

check-py:
	-for f in $(TESTS) ; do echo ==== $$f; \
	  PYTHONPATH=. $(PYTHON) $$f; \
	done

check-sh:
	-for f in tests/*test.sh ; do echo ==== $$f; \
	  PYTHONPATH=. $$f; \
	done

# Run all tests while checking code coverage
coverage:	report

# Show summary of 
report:	.coverage
	python-coverage -r --omit=/usr/share/pyshared/\*

# Create annotated version of files with line-by-line coverage
annotate:	.coverage
	[ -d .cover-files ] || mkdir .cover-files
	python-coverage annotate -d .cover-files *.py
	@echo "Results are in: .cover-files"

# python-coverage stores it's data in .coverage
.coverage:	*.py tests/*.py Makefile
	-for f in $(TESTS) ; do echo ==== $$f; \
	  PYTHONPATH=. $(PYTHON-COVERAGE) -x $$f; \
	done

clean:
	rm -f *.pyc .coverage
	rm -rf .cover-files

pychecker:
	pychecker --only --maxargs 12 *.py tests/*.py
