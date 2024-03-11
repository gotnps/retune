// Presented by BrilliantPy v.1.0.1
/*######################### Editable1 Start #########################*/
let SHEETNAME = "Selling data bot";
let SS_ID = "1t2dx5vIzXrwmtlQkq5RgdObVQHX1KLLI2Ax0zxQj7N4";
/*#########################  Editable1 End  #########################*/
// Init
let ss, sheet, lastRow, lastCol, range, values, data;
Logger = BetterLog.useSpreadsheet(SS_ID);

function doPost(e) {
    initSpreadSheet();
    try {
        let req_content = e.postData.contents;
        let event_0 = JSON.parse(req_content).events[0];
        let user_msg = event_0.message.text;
        let token = event_0.replyToken;
        let replyText = "";

        if (event_0.message.type === "text") {
            let index = user_msg.indexOf('\n');
            if (index !== -1) {
                let command = user_msg.slice(0, index).trim().toLowerCase();
                let info = user_msg.slice(index + 1).trim();
                Logger.log('command: '+command);
                Logger.log('info: '+info);
                
                switch (command) {
                    case 'add ticket':
                        replyText = addTicket(info);
                        break;
                    case 'fee':
                        let [feeRate, feeAmount] = calFee(info.trim());
                        replyText = 'fee rate : ' + feeRate + '\nfee amount : ' + feeAmount;
                        break;
                    case 'update':
                        replyText = updateStatus(info);
                        break;
                    case 'find':
                        replyText = findAllTickets(info);
                        break;
                    case 'edit':
                        replyText = editInfo(info);
                        break;
                    case 'change price':
                        replyText = changeSellingPrice(info);
                        break;
                }
            }else{
                if(user_msg.trim().toLowerCase() == 'find all available concert'){
                    replyText = findAlllConcert();
                } else {
                    return;
                }
            }
            
            if (replyText) {
                replyMessage(token, replyText);
            }
        }
    } catch (e) {
        Logger.log("doPost error:" + e);
    }
}

function findAlllConcert(){
    let concertCounts = {};
    const concertNameCol = findColumnIndex('concert name');
    const statusCol = findColumnIndex('ticket status');
    for(let i=1; i<data.length; i++){
        let row = data[i];
        let status = row[statusCol].toLowerCase();
        let concertName = row[concertNameCol];

        if(status ==  "available"){
            Logger.log(concertName);
            if(concertCounts.hasOwnProperty(concertName)) {
                concertCounts[concertName] ++;
            }
            else {
                concertCounts[concertName] = 1;
            }
        }
    }
    Logger.log(concertCounts);
    let result = "";
    for(let concert in concertCounts) {
        result += concert +  ": " + concertCounts[concert] + "\n";
    }
    Logger.log(result);
    return result !== "" ? result : 'No available ticket';
}

function addTicket(ticketInfo) {
    let ticketObject = {};
    let infoArray = ticketInfo.split(/\n/);
    
    infoArray.forEach(pair => {
      const [key, value] = pair.split(':').map(item => item.trim());
      ticketObject[key.toLowerCase()] = value;
    });
  
    ticketObject['ticket status'] = 'available';
  
    const [feeRate, feeAmount] = calFee(ticketObject['selling price']);
    ticketObject['fee rate'] = feeRate;
    ticketObject['buyer fee'] = feeAmount;
    ticketObject['seller fee'] = ticketObject['have seller'] === 'true' ? feeAmount : 0;
    ticketObject['profit'] = 0;
    ticketObject['date added'] = getDate();
  
    const amount = parseInt(ticketObject['amount']);
    delete ticketObject['amount'];
  
    const addedIds = [];
  
    for (let i = 1; i <= amount; i++) {
      const id = generateId(ticketObject['concert name']);
      ticketObject['id'] = id;
      addedIds.push(id);
      setValuesToLastRow(ticketObject);
    }
  
    const allId = addedIds.join(',');
    return "Ticket(s) " + allId + " added";
  }
  

function updateStatus(data) {
    const lines = data.split(/\n/);
    let results = [];
  
    for (let line of lines) {
      let [id, status] = line.split(' ').map(item => item.trim());
      status = status.toLowerCase();
      id = id.toUpperCase();
      const rowIndex = findRowIndexByValue('id', id);
  
      if (rowIndex === -1) {
        results.push(`Can't find ID: ${id}`);
        continue;
      }
  
      if (status !== 's' && status !== 'un' && status !== 'a') {
        results.push(`${id}: Invalid status`);
        continue;
      }
  
      let profit = 0;
  
      if (status === 'a') {
        status = 'available';
      } else if (status === 's') {
        status = 'sold';
        const sellerFee = getValue('seller fee', rowIndex);
        const buyerFee = getValue('buyer fee', rowIndex);
        const sellingPrice = getValue('selling price', rowIndex);
        const ticketPrice = getValue('ticket price', rowIndex);
        const haveSeller = String(getValue('have seller', rowIndex)).toLowerCase() === 'true';
        
        profit = haveSeller ? sellerFee + buyerFee : sellingPrice - ticketPrice + buyerFee;
      } else {
        status = 'unavailable';
      }
  
      setValue('profit', rowIndex, profit);
      setValue('ticket status', rowIndex, status);
      setValue('update date', rowIndex, getDate());
      
      results.push(`Updated ${id} to ${status}`);
    }
  
    return results.join('\n');
  }
  

function editInfo(data) {
    const infoList = data.split(/\n/);
    const id = infoList[0].toUpperCase();
    const rowIndex = findRowIndexByValue('id', id);
    let result = [];
    if (rowIndex === -1) {
        return `Can't find ID: ${id}`;
    }
    result.push('Set ' + id);
    for (let i = 1; i < infoList.length; i++) {
        const [key, value] = infoList[i].split(':').map(item => item.trim());
        if (value !== "") {
            setValue(key.toLowerCase(), rowIndex, value);
            result.push(`${key}: ${value}`);
        }
    }
    return result.join('\n');
}


function findAllTickets(partialName) {
    Logger.log('partial name : '+ partialName);
    let result = [];
    const concertNameCol = findColumnIndex('concert name');
    const statusCol = findColumnIndex('ticket status');
    const idCol = findColumnIndex('id');
    const saCol = findColumnIndex('seller account');
    const spCol = findColumnIndex('seller platform');
    const tpCol = findColumnIndex('ticket price');
    const sellpCol = findColumnIndex('selling price');
    const condateCol = findColumnIndex('concert date');
    for (var i = 1; i < data.length; i++) { // Assuming row 1 is header
        const concertName = data[i][concertNameCol];
        const status = data[i][statusCol];
        
        let regex = new RegExp(partialName, 'i'); // 'i' flag for case-insensitive search
        
        if (status === "available" && regex.test(concertName)) {
            result.push("["+data[i][idCol]+"]");
            let concertdate = data[i][condateCol]
            if(concertdate != ""){
                concertdate = new Date(concertdate);
                const formattedDate = ('0' + concertdate.getDate()).slice(-2) + '/' + ('0' + (concertdate.getMonth() + 1)).slice(-2) + '/' + concertdate.getFullYear();
                result.push(formattedDate);
            }
            result.push(data[i][saCol] + " : " + data[i][spCol]);
            result.push(data[i][tpCol] + " sell " + data[i][sellpCol]);
        }
    }
    if (result.length === 0) {
        return 'No ticket available';
    }
    return result.join("\n");
}

function changeSellingPrice(data) {
    const lines = data.split(/\n/);
    let result = [];
    let idChanged = [];
    for (let line of lines) {
        const [id, price] = line.trim().split(/\s+/);
        const rowIndex = findRowIndexByValue('id', id);
        if (rowIndex === -1) {
            result.push(`Can't find ID: ${id}`);
            continue;
        }
        const [feeRate, feeAmount] = calFee(price);
        const haveSeller = String(getValue('have seller', rowIndex)).toLowerCase() === 'true';
        setValue('selling price', rowIndex, price);
        setValue('buyer fee', rowIndex, feeAmount);
        setValue('fee rate', rowIndex, feeRate);
        if (haveSeller) {
            setValue('seller fee', rowIndex, feeAmount);
        }
        idChanged.push(id);
    }
    result.push(`IDs changed: ${idChanged.join(', ')}`);
    
    return result.join("\n");
}


function setValuesToLastRow(columnValues) {
    const lastRow = sheet.getLastRow() + 1; // Next row after the last row
    const headerRowValues = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
    const valuesToSet = [];
  
    for (const columnName of headerRowValues) {
      const value = columnValues[columnName.toLowerCase()] !== undefined ? columnValues[columnName.toLowerCase()] : ""; // Use bracket notation to access values
      valuesToSet.push(value);
    }
  
    sheet.getRange(lastRow, 1, 1, valuesToSet.length).setValues([valuesToSet]);
}
  


function setValue(colname, rowi, value) {
  const coli = findColumnIndex(colname);
  sheet.getRange(rowi + 1, coli + 1).setValue(value);
}

function getValue(colname, rowi) {
    const coli = findColumnIndex(colname);
    return data[rowi][coli]; // Access data from the global variable
}

function findColumnIndex(colname) {
    const header = data[0]; // Header is in the first row of data
    return header.indexOf(colname);
} 

function findRowIndexByValue(colname, value) {
    let coli = findColumnIndex(colname);
  
    for (let rowIndex = 1; rowIndex < data.length; rowIndex++) { // Start from index 1 to skip the header row
        if (data[rowIndex][coli] === value) {
            return rowIndex;
        }
    }
    return -1;
  }

function calFee(sellingPrice) {
  if (0 < sellingPrice && sellingPrice <= 1000) {
      return ['fixed rate', 100];
  }
  else if (1000 < sellingPrice && sellingPrice <= 3000) {
      return ['fixed rate', 150];
  }
  else if (3000 < sellingPrice && sellingPrice <= 5000) {
      return [5, Math.ceil(sellingPrice * 5 / 100)];
  }
  else {
      return [3.5, Math.ceil(sellingPrice * 3.5 / 100)];
  }
}

function generateId(concertName) {
  let id = concertName.toUpperCase().replace(/[^A-Z]/g, '');
  id = id.substring(0, 3);
  return id + String(sheet.getLastRow());
}

function getDate() {
    let currentDate = new Date();
    let day = currentDate.getDate().toString().padStart(2, '0');
    let month = (currentDate.getMonth() + 1).toString().padStart(2, '0'); // Month is zero-indexed, so add 1
    let year = currentDate.getFullYear();
  
    return `${day}/${month}/${year}`;
}

function initSpreadSheet() {
    ss = SpreadsheetApp.getActive();
    sheet = ss.getSheetByName(SHEETNAME);
    lastRow = sheet.getLastRow();
    lastCol = sheet.getLastColumn();
    range = sheet.getDataRange();
    values = range.getValues();
    data = range.getValues()
    Logger.log('initSpreadSheet completed');
    // Logger.log('lastRow :'+lastRow);//last == empty one
    // Logger.log('lastCol :'+lastCol);
}

async function replyMessage(token, replyText) {
    let url = "https://api.line.me/v2/bot/message/reply";
    let lineHeader = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + CHANNEL_ACCESS_TOKEN
    };

    let postData = {
        "replyToken": token,
        "messages": [{
            "type": "text",
            "text": replyText
        }]
    };
    // let postData = {
    //   "replyToken" : token,
    //   "messages" : [flex_obj]
    // };

    let options = {
        "method": "POST",
        "headers": lineHeader,
        "payload": JSON.stringify(postData)
    };

    try {
        let response = await UrlFetchApp.fetch(url, options);
        Logger.log("response:" + response);
    }

    catch (error) {
        Logger.log(error.name + ":" + error.message);
        return;
    }

    if (response.getResponseCode() === 200) {
        Logger.log("Sending message completed.");
    }
}