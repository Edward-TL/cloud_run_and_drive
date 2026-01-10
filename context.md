This project is a cloud run service that receives data from a Wix API POST request with a JSON body of the format shown on the example:

```json
{
    "plan_valid_until":"12/03/21",
    "owner_subscription_universal_link":"https://manage.wix.com/dashboard/00000000-0000-0000-0000-000000000000/subscriptions/00000000-0000-0000-0000-000000000000",
    "site_email":"business@mywebsite.com",
    "plan_order_id":"02be614d-dd1e-49bd-b08a-a37a2fe2e0b1",
    "plan_description":"Beginners Yoga Course",
    "plan_id":"02be614d-dd1e-49bd-b08a-a37a2fe2e0b1",
    "site_name":"My Site",
    "plan_title":"Yoga Course",
    "plan_price":{
        "value":"20",
        "currency":"USD",
    },
    "plan_start_date":"10/12/20",
    "contact_id":"edca2245-7ce3-4d95-bfe9-b2012110eb8f",
    "plan_cycle_duration":"2 months",
    "contact":{
    "name":{
        "last":"Brooks",
        "first":"Jamie",
    },
    "email":"example@email.com",
    "locale":"pt",
    "company":"ACME Inc.",
    "birthdate":"1986-06-12",
    "labelKeys":{
        "items":[
            "contacts.contacted-me",
            "custom.my-label",
        ],
    },
    "contactId":"fab5801757de494d94e45b264ef5c3ec",
    "address":{
        "city":"San Francisco",
        "addressLine":"123 Main Street",
        "formattedAddress":"123 Main Street, San Francisco, United States",
        "country":"US",
        "postalCode":"94158",
        "addressLine2":"Building 6, 3rd floor",
        "subdivision":"US-CA",
    },
    "jobTitle":"CEO",
    "imageUrl":"https://images-wixmp-7ef33.wixmp.com",
    "updatedDate":"2023-08-25T15:00:00.000Z",
    "phone":"+14046666666",
    "createdDate":"2023-08-25T15:00:00.000Z",
    },
},
```

At helpers.py, you will create next:
1. flat_dictionary: Function required to flattern the json into a unique list of dictionaries, where the keys are made using a formatted string, and the values are the values of the json. The keys will consider to use the root of the dictionary as a prefix, and the key of the dictionary as the suffix, separated by an underscore.

2. update_excel: Function required to update the excel file with the data received from the Wix API. The excel file will be stored at a Google Drive folder, so consider to use the Google Drive API to update the file. 

At main.py, you will create next:
1. load_to_excel: Function required to receive the data from the Wix API and call the functions created at helpers.py. In case the excel file is not created, it will be created with the data of the dictionary, using the keys as headers of the table.