# Bundle Packer Unpacker
Tool to unpack and pack Criterion Games' bundle files

## Usage
Command-line usage: `python bundle_packer_unpacker.py [option] <game> <input_file> <output_dir> <output_name>`

Options:  
`-h`, `--help`      Show this help message  
`-v`, `--version`   Show the tool version  
`-u`, `--unpack`    Unpack an given bundle file to the specified output directory  
`-p`, `--pack`      Pack an given resource table to the specified output directory and name it with the specified output name  

Other input data:  
       `<game>`     The game the file is from/to: BP, HP, HPR or MW  
 `<input_file>`     Input file or directory path  
 `<output_dir>`     Output directory  
`<output_name>`     Output file name, only for -p and --pack option  

## Tutorial
- [Unpack and repack BNDL with Python script](https://docs.google.com/document/d/1rbCo7kI9R6x32whL0RI0YT-bmP64-sFcreRaA95BLok)
