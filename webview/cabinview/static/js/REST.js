
/*
REST API
*/

/* Common REST API GET Method */
function REST_GET(url){
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    return fetch(url, {
        method: "GET",
		headers: { "Content-Type": "application/json; charset=utf-8", 'X-CSRFToken': csrftoken },
        credentials: "same-origin",
		cache:'no-cache',
		redirect:'follow',
		referrer:'no-referrer',
    });
}

function REST_POST(url, data){
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
	return fetch(url, {
        method: "POST",
		headers: { "Content-Type": "application/json; charset=utf-8", 'X-CSRFToken': csrftoken },
        credentials: "same-origin",
		cache:'no-cache',
		redirect:'follow',
		referrer:'no-referrer',
		body: JSON.stringify(data),
    });
}


/*
 general API for fetching url
*/
function restapi_request_general_get(url, args, method="GET"){
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    return fetch(url, {
        method: method,
		headers: {
            "Content-Type": "application/json; charset=utf-8",
			'X-CSRFToken': csrftoken
        },
        credentials: "same-origin",
		cache:'no-cache',
		redirect:'follow',
		referrer:'no-referrer',
        body: args,
    })
    .then(function(response){
        return response.json();
    });
}

/*
 Request the list of data tags(fields) of database
*/
function restapi_request_ts_datatags(db){
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    return fetch('/api/db/'+db+"/", {
        method: "GET",
		headers: {
            "Content-Type": "application/json; charset=utf-8",
			'X-CSRFToken': csrftoken
        },
        credentials: "same-origin",
		cache:'no-cache',
		redirect:'follow',
		referrer:'no-referrer',
    })
    .then(function(response){
        return response.json();
    });
}


/*
 Request the list of time series database name which is already created
*/
function restapi_request_ts_databases(){
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    return fetch('/api/db/', {
        method: "GET",
		headers: {
            "Content-Type": "application/json; charset=utf-8",
			'X-CSRFToken': csrftoken
        },
        credentials: "same-origin",
		cache:'no-cache',
		redirect:'follow',
		referrer:'no-referrer',
    })
    .then(function(response){
        return response.json();
    });
}

/*
 Request the collection of the time series database with tags
*/
function restapi_request_ts_collect(db, tags){
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    return fetch('/api/db/'+db+'/collect?tags='+tags.join(","), {
        method: "GET",
		headers: {
            "Content-Type": "application/json; charset=utf-8",
			'X-CSRFToken': csrftoken
        },
        credentials: "same-origin",
		cache:'no-cache',
		redirect:'follow',
		referrer:'no-referrer',
    })
    .then(function(response){
        return response.json();
    });
}
