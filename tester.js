// Presented by BrilliantPy v.1.0.1
/*######################### Editable1 Start #########################*/
let SHEETNAME = "Sheet1";
let SS_ID = "17rZDHOtvBjMOCS_4JyJzqkhcFIpcYo0UjZ2t9mx4VoM";
/*#########################  Editable1 End  #########################*/
// Init
let ss, sheet, lastRow, lastCol, range, values;
Logger = BetterLog.useSpreadsheet(SS_ID);

function doPost(e) {
  initSpreadSheet();
  // Logger.log(SS_ID);
  // Logger.log(SHEETNAME);
  try {
      let req_content = e.postData.contents;
      // Logger.log("req_content:"+req_content);

      let event_0 = JSON.parse(req_content).events[0];
      let user_msg = event_0.message.text;
      // Logger.log("user_msg:"+user_msg);

      let token = event_0.replyToken;
      let replyText = "";
      const command = user_msg.split('*')[0].trim();
      const data = user_msg.split('*')[1].trim();

      Logger.log('command :' + command);
      Logger.log('data :' + data);

      if (command == 'add ticket') {
          replyText = addTicket(data);
      }
      else if (command == 'fee') {
          let [feeRate, feeAmount] = calFee(data.trim());
          replyText = 'fee rate: ' + String(feeRate) + '\nfee amount: ' + String(feeAmount);
      }
      else if (command == 'update') {
          replyText = updateStatus(data);
      }
      else if(command == 'find'){
          replyText = findAllTicket(data);
      }
      else if(command == 'edit'){
        replyText = editInfo(data);
      }
      else if(command == 'change price') {
        replyText = changeSellingPrie(data);
      }

    //   else if(command == "test"){
    //     replyText = testtrim(data);
    //   }
      if (event_0.message.type === "text") {
          if (replyText) {
              replyMessage(token, replyText);
          }
      }
  } catch (e) {
      Logger.log("doPost error:" + e);
  }
}

function addTicket(ticketInfo) {
  initSpreadSheet();
  //-------------------create map---------------------//
  const ticketMap = new Map();
  const infoArray = ticketInfo.split(/\n/);
  infoArray.forEach(pair => {
      const [key, value] = pair.split(':').map(item => item.trim());
      ticketMap.set(key.toLowerCase(), value);
  });
  ticketMap.set('ticket status', 'available');
  let [feeRate, feeAmount] = calFee(ticketMap.get('selling price'));
  ticketMap.set('fee rate', feeRate);
  ticketMap.set('buyer fee', feeAmount);
  if (ticketMap.get('have seller') == 'true') {
      ticketMap.set('seller fee', feeAmount);
  }
  else {
      ticketMap.set('seller fee', 0);
  }
  ticketMap.set('profit', 0);
  let date = getDate();
  ticketMap.set('date added', date);

  //-------------------insert to speadsheet---------------------//
  const amount = ticketMap.get('amount');
  ticketMap.delete('amount');
  let allId = String();
  for(let i=1;i<=amount;i++){
    const id = generateId(ticketMap.get('concert name'));
    ticketMap.set('id', id);
    allId += `${id},`;
    let lastRow = sheet.getLastRow();
    for (let [key, value] of ticketMap.entries()) {
        let columnIndex = findColumnIndex(key);
        if (columnIndex == -1) {
            return "can't find column" + String(key);
        }
        sheet.getRange(lastRow + 1, columnIndex + 1).setValue(value);
    }
  }
  return "ticket " + allId + " added";
}

function updateStatus(data) {
  initSpreadSheet();
  const lines = data.split(/\n/);
  let result = String();
  for(let line of lines) {
    const [id, status] = line.split(' ').map(item => item.trim());
    const rowIndex = findRowIndexByValue('id', id);
    if (rowIndex == -1) {
        result += 'cant find ' + id + '\n';
        continue;
    }
    if(status != 'sold' && status != 'unavailable'){
        result += id + 'invalid status' + '\n';
        continue;
    }
    if(status == 'sold'){
        let sellerFee = getValue('seller fee',  rowIndex);
        let buyerFee = getValue('buyer fee', rowIndex);
        let sellingPrice = getValue('selling price', rowIndex);
        let ticketPrice = getValue('ticket price', rowIndex);
        let haveseller  = getValue('have seller', rowIndex);
        let profit;
        if(String(haveseller).toLowerCase() == 'true') {
            profit = sellerFee + buyerFee;
        }
        else {
            profit = sellingPrice - ticketPrice + buyerFee;
        }
        setValue('profit', rowIndex, profit);
    }
    setValue('ticket status', rowIndex, status);
    setValue('update date', rowIndex, getDate());
    result += 'updated ' + id + ' to ' + status + '\n';
  }
  return result;
}
function editInfo(data){
    const infoList = data.split(/\n/);
    const id = infoList[0].toUpperCase();
    const rowIndex = findRowIndexByValue('id' , id);
    let result = String();
    if(rowIndex == -1){
        return 'cant find ' + id;
    }
    result += 'set ' + id + '\n';
    for(let i =1; i<infoList.length; i++){
        const [key, value] = infoList[i].split(':').map(item => item.trim());
        if(value == "") {continue;}
        setValue(key, rowIndex, value);
        result += key + ' : '+ value +'\n';
    }
    return result;
}

function findAllTicket(data) {
//   Logger.log('find all ticket');
//   Logger.log(data)
  const idstr = data.toUpperCase();
//   Logger.log('idstr ' +idstr);
  colIndex = findColumnIndex('id');
  values = sheet.getRange(2,colIndex+1,sheet.getLastRow()-1,1).getValues();
//   Logger.log(values);
  let result = String();
  for(let i=0;i<values.length;i++){
      const status = getValue( 'ticket status', i+1 );
      // Logger.log(values[i][0].toString().substring(0,3) + " " + status)
      if((status == 'available') && (values[i][0].toString().substring(0,3) == idstr)) {
          result += "["+getValue('id', i+1) +"]"+ "\n";
          result += getValue('seller account', i+1) +": "+getValue('seller platform', i+1)+"\n";
          result += getValue('ticket price', i+1) + ' sell '+getValue('selling price', i+1)+'\n';
      }
  }
//   Logger.log(result);
  if(result.length == 0){
    return "no available ticket";
  }
  return result
}

function changeSellingPrie(data){
    let dataList = data.split(/\s|\n/);
    const ids = dataList.slice(0, dataList.length-1);
    const price = dataList[dataList.length -1];
    Logger.log('dataList: '+dataList);
    Logger.log('ids: '+ids);
    Logger.log('price: '+price);
    const [feeRate, feeAmount] = calFee(price);
    Logger.log(feeRate+' '+feeAmount);
    for(id of ids) {
        const rowIndex = findRowIndexByValue('id', id);
        const haveseller = String(getValue('have seller', rowIndex)).toLowerCase();
        if(haveseller == 'true') {
            setValue('seller fee', rowIndex, feeAmount);
        }
        setValue('selling price', rowIndex,  price);
        setValue('buyer fee', rowIndex, feeAmount);
        setValue('fee rate', rowIndex, feeRate);
    }
    return 'successfully changed the selling price!';
}


function setValue(colname, rowi, value) {
  const coli = findColumnIndex(colname);
  sheet.getRange(rowi + 1, coli + 1).setValue(value);
}

function getValue(colname, rowi) {
  const coli = findColumnIndex(colname);
  return sheet.getRange(rowi + 1, coli + 1).getValue();
}

function findColumnIndex(columnName) {
  const header = sheet.getRange(1, 1, 1, lastCol).getValues()[0]
  return header.indexOf(columnName);
}

function findRowIndexByValue(colname, value) {
  let coli = findColumnIndex(colname);

  const columnValues = sheet.getRange(1, coli+1, sheet.getLastRow(), 1).getValues();
  for (let rowIndex = 0; rowIndex < columnValues.length; rowIndex++) {
      if (columnValues[rowIndex][0] === value) {
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
  let year = currentDate.getFullYear();
  let month = (currentDate.getMonth() + 1).toString().padStart(2, '0'); // Month is zero-indexed, so add 1
  let day = currentDate.getDate().toString().padStart(2, '0');

  return `${year}-${month}-${day}`;
}

function initSpreadSheet() {
    ss = SpreadsheetApp.getActive();
    sheet = ss.getSheetByName(SHEETNAME);
    lastRow = sheet.getLastRow();
    lastCol = sheet.getLastColumn();
    range = sheet.getDataRange();
    values = range.getValues();
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