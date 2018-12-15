# msemu

* clone repository
* cd msemu
* with virtualenv:
* pip3 install --user virtualenv
* virtualenv --python=/usr/bin/python3 env
* source env/bin/activate
* pip install -e .

* source env/bin/activate
* make build

# changing the CTLE transfer function
* go to msemu/msemu/ctle.py, then add your own values for "num" and "den" (on line 139)
* comment out lines 125-135 because they are specific to the PCIe reference CTLE design

# changing the channel response
* go to the top-level msemu directory
* mkdir channel (if it doesn't exist)
* put your s-parameter file in the channel directory
* go to msemu/msemu/rf.py, then change the "file_name" value to the name of your s-parameter file
* the s-parameter file should be S4P (four port) and the port assignment numbers must match figure 3 of https://www.aesa-cortaillod.com/fileadmin/documents/knowledge/AN_150421_E_Single_ended_S_Parameters.pdf

# if you only have one "CTLE" mode
* to avoid building 16 different models, go to msemu/msemu/ctle.py.
* on line 85, change to "db_vals = list(range(2))".  
