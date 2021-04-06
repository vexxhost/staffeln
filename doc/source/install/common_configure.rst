2. Edit the ``/etc/staffeln/staffeln.conf`` file and complete the following
   actions:

   * In the ``[database]`` section, configure database access:

     .. code-block:: ini

        [database]
        ...
        connection = mysql+pymysql://staffeln:STAFFELN_DBPASS@controller/staffeln
