
class CommandController:
    def __init__(self, base_classes, requests_manager, data_manager, communication_manager, parse_manager):
        self.basecl = base_classes
        self.reqM = requests_manager
        self.dataM = data_manager
        self.commM = communication_manager
        self.parseM = parse_manager

        for attr_name in dir(self):
            attribute = getattr(self, attr_name)

            if callable(attribute):
                if attr_name.startswith("cmd_") or attr_name == "executeCommand":
                    handle_network_exc = True if attr_name.startswith("cmd_net_") else False
                    setattr(self, attr_name, self.commM.handleCommonExceptions(attribute, attr_name, handle_network_exc))

    def executeCommand(self, arguments, flags):
        arguments_len = len(arguments)

        command = arguments[0] if arguments else "help"
        subcommand = arguments[1] if arguments_len > 1 else None
        left_arguments = list(set(arguments) - {command, subcommand}) if arguments_len > 2 else None

        command_handlers = {
            "status": lambda: self.cmd_status(),
            "update": lambda: self.cmd_net_update(self.commM.printAndGetAccessToken()),
            "alter": lambda: self.cmd_net_alter(self.commM.printAndGetAccessToken(), subcommand, flags, left_arguments),
            "help": lambda: self.cmd_help()
        }
        
        command_handler = command_handlers.get(command)
        if command_handler:
            command_handler()
        else: 
            self.commM.printErrorAndExit("Invalid command. To check the list of available commands, run 'help'")
    
    #-------------------------------

    def cmd_status(self):

        def printNested(key, value, indent = 2):
            prefix = "  " * indent

            if isinstance(value, dict):  
                self.commM.printText(f"{prefix}> {key}:")
                for sub_key, sub_value in value.items():
                    printNested(sub_key, sub_value, indent + 2)
            else:
                self.commM.printText(f"{prefix}> {key}: {value}")
        
        #-------------------------------

        path = self.dataM.paths.get("repository_data_file")

        repositories_list = self.dataM.readJsonFile(path)
        if repositories_list is None:
            token = self.commM.printAndGetAccessToken()
            self.update(token)
            repositories_list = self.dataM.readJsonFile(path)
        
        for repository_dict in repositories_list:
            self.commM.printText(f"For repository '{repository_dict.get('name')}'")
        
            for key, value in repository_dict.items():
                if key == 'name':
                    continue
                printNested(key, value)
            
            if len(repositories_list) > repositories_list.index(repository_dict) + 1:
                self.commM.printText()
                
                

    def cmd_net_update(self, token):
        repository_names = self.reqM.fetchRepositoryNames(token)
        username = self.reqM.fetchUsername(token)
        
        repositories = list()

        for repository_name in repository_names:
            main_response = self.reqM.makeRequest("get", f"/repos/{username}/{repository_name}", token) 
            main_response.raise_for_status()

            main_repository_info = main_response.json()

            repository = self.basecl.Repository(
            main_repository_info.get("name"), 
            main_repository_info.get("id"), 
            main_repository_info.get("delete_branch_on_merge"))

            repositories.append(repository.__dict__)
        
        path = self.dataM.paths.get("repository_data_file")
            
        self.dataM.writeJsonFile(path, repositories)
        self.commM.printText("Repository status updated successfully.")


    def cmd_net_alter(self, token, subcommand, flags = None, requested_repo_names = None):
        repository_names = None
        username = None

        def setFeature(body, method, path = ""):
            json_string = self.parseM.dictToJsonString(body)

            for repository_name in repository_names:
                self.reqM.makeRequest(method, f"/repos/{username}/{repository_name}" + path, token, json_string)
        
        #-------------------------------
        
        def toggleFeature(name, method, path = ""):
            flags_dictionary = self.parseM.flagsToDictionary(flags)
            enabled = flags_dictionary.get("_main_")
            
            if enabled == True or enabled == False:
                body = {name: enabled}
                setFeature(body, method, path)
            else:
                self.commM.printInvalidFlagsAndExit()
                
        #-------------------------------

        def cmd_auto_delete_head():
            toggleFeature("delete_branch_on_merge", "patch")
        
        #-------------------------------

        subcommand_handler = locals().get(f"cmd_{subcommand}")
        if subcommand_handler:

            repository_names = self.reqM.fetchRepositoryNames(token, requested_repo_names)
            username = self.reqM.fetchUsername(token)

            subcommand_handler()
        else:
            self.commM.printInvalidSubcommandAndExit()
        
        self.commM.printText("Repository status altered successfully.")
        self.cmd_net_update(token)
        

    def cmd_help(self):
        path = self.dataM.paths.get("help_file")
        try:
            self.commM.printText(self.dataM.readFile(path))
        except:
            self.commM.printErrorAndExit("The Help file could not be found. Please make sure the 'help.txt' file is located in the 'data' directory.")


