// File run by github workflow to update the ProgramIndex.json file.

const fs = require("fs");
const fetch = require('node-fetch-commonjs');

const toIndex = "4969978486505472";
let queries = []

// Load in the current index of programs.
let index = JSON.parse(fs.readFileSync("./ProgramIndex.json").toString());

async function getSpinOffs(id, cursor="") {
    // Setup request
    const queryName = "listTopProgramSpinoffs";
    const query = queries[queryName];
    const variables = {
        "sort": "RECENT",
        "from": {
            "kind": "PROGRAM",
            "programOrContentId": toIndex
        },
        "pageInfo": {
            "cursor": cursor,
            "itemsPerPage": 30  // I'd like to do more but I want this request to appear standard
        }
    }

    // fetch
    const response = await (await fetch("https://www.khanacademy.org/api/internal/graphql/"+queryName, {
        "method": 'POST',
        "body": JSON.stringify({
            "operationName": queryName,
            "query": query,
            "variables": variables
        }) 
    })).json();

    return response.data.listTopProgramSpinoffs;
}

// Async function so we can await
(async function main(){
    // Boilerplate done

    // First get latest queries
    queries = await (await fetch("https://cdn.jsdelivr.net/gh/bhavjitChauhan/khan-api@safelist/queries.json")).json()
    
    // We are going to read up until we find a program newer than this.
    let lastReadDate = new Date( Number(fs.readFileSync("./system/lastReadDate.txt").toString()) )

    // Store the index we are currently searching
    let cursor = "";

    let indexing = true;
    while (indexing) {
        let response = await getSpinOffs(toIndex);
        let programs = response.programs;
        cursor = response.cursor;
        
        // Index each of these programs
        console.log(response)

        // Check if we hit the end of available programs
        if (response.complete) {
            indexing = false
        }

        // If we are still indexing, we've updated the cursor, so we're free to continue te loop to the next cursor.
    }

    // Finally write the index
    fs.writeFileSync("./UpdateProgramIndex.js", JSON.stringify(index))
})()


