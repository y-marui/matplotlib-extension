update-charter:
	git remote | grep -q '^dev-charter$$' || \
	  git remote add dev-charter https://github.com/y-marui/dev-charter
	git fetch dev-charter
	git subtree pull --prefix=docs/dev-charter dev-charter main --squash
