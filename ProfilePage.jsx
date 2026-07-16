import { useEffect, useState } from "react";
import api from "../api";
import { useAuth } from "../context/AuthContext";

function ProfilePage() {

  const { refreshUser } = useAuth();

  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");

  const [message, setMessage] = useState("");

  const [passwordMessage, setPasswordMessage] = useState("");

  const [avatarFile, setAvatarFile] = useState(null);
  const [avatarMessage, setAvatarMessage] = useState("");

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");



  useEffect(() => {
    fetchProfile();
  }, []);



  const fetchProfile = async () => {

    try {

      const res = await api.get("/api/me");

      setProfile(res.data);

      setName(res.data.name);

      setEmail(res.data.email);


    } catch (err) {

      console.error("Profile fetch error:", err);

    } finally {

      setLoading(false);

    }

  };




  const updateProfile = async () => {

    setMessage("");

    try {

      const res = await api.put("/api/me", {
        name,
        email
      });


      setMessage(res.data.message);


      setProfile((prev)=>({
        ...prev,
        name,
        email
      }));


      refreshUser();



    } catch(err){

      setMessage(
        err.response?.data?.message ||
        "Failed to update profile"
      );

    }

  };




  const updatePassword = async () => {


    setPasswordMessage("");


    if(
      !currentPassword ||
      !newPassword ||
      !confirmPassword
    ){

      setPasswordMessage(
        "All fields are required"
      );

      return;

    }



    try {


      const res = await api.put(
        "/api/me/password",
        {
          current_password: currentPassword,
          new_password: newPassword,
          confirm_password: confirmPassword
        }
      );



      setPasswordMessage(
        res.data.message
      );


      setCurrentPassword("");

      setNewPassword("");

      setConfirmPassword("");



    } catch(err){


      setPasswordMessage(
        err.response?.data?.message ||
        "Password update failed"
      );


    }


  };






  const uploadAvatar = async () => {


    if(!avatarFile){

      setAvatarMessage(
        "Please select an image"
      );

      return;

    }



    try {


      const formData = new FormData();


      formData.append(
        "image",
        avatarFile
      );



      const res = await api.post(
        "/api/upload",
        formData
      );



      setAvatarMessage(
        res.data.message
      );



      fetchProfile();


      refreshUser();



    }catch(err){


      setAvatarMessage(
        err.response?.data?.message ||
        "Avatar upload failed"
      );


    }


  };






  if(loading || !profile){

    return <h3>Loading...</h3>;

  }






  return (

    <div
      style={{
        maxWidth:"600px",
        margin:"40px auto",
        padding:"20px",
        border:"1px solid #ddd",
        borderRadius:"10px"
      }}
    >


      <h2>My Profile</h2>


      <hr />



      {/* Avatar */}


      <div style={{marginBottom:"20px"}}>


        <strong>Avatar</strong>


        <br />



        {
          profile.avatar_url ? (

            <img
              src={
                `http://127.0.0.1:5000${profile.avatar_url}`
              }
              alt="Profile"
              width="120"
              height="120"
              style={{
                marginTop:"10px",
                borderRadius:"50%",
                objectFit:"cover",
                border:"2px solid #ccc"
              }}
            />


          ) : (

            <p>No Avatar</p>

          )

        }



        <br />


        <input

          type="file"

          accept="image/*"

          onChange={
            (e)=>setAvatarFile(
              e.target.files[0]
            )
          }

        />



        <br />



        <button

          onClick={uploadAvatar}

          style={{
            marginTop:"10px",
            padding:"10px 20px",
            cursor:"pointer"
          }}

        >

          Upload Avatar


        </button>



        {
          avatarMessage && (

            <p style={{
              color:"green",
              fontWeight:"bold"
            }}>

              {avatarMessage}

            </p>

          )
        }



      </div>





      {/* Name */}


      <div style={{marginBottom:"20px"}}>


        <label>
          <strong>Name</strong>
        </label>


        <br />


        <input

          type="text"

          value={name}

          onChange={
            (e)=>setName(e.target.value)
          }

          style={{
            width:"100%",
            padding:"10px"
          }}

        />


      </div>






      {/* Email */}


      <div style={{marginBottom:"20px"}}>


        <label>
          <strong>Email</strong>
        </label>


        <br />


        <input

          type="email"

          value={email}

          onChange={
            (e)=>setEmail(e.target.value)
          }

          style={{
            width:"100%",
            padding:"10px"
          }}

        />


      </div>





      <button

        onClick={updateProfile}

        style={{
          padding:"10px 20px",
          cursor:"pointer"
        }}

      >

        Save Changes


      </button>




      {
        message && (

          <p style={{
            color:"green",
            fontWeight:"bold"
          }}>

            {message}

          </p>

        )
      }







      <hr />



      <h2>
        Change Password
      </h2>




      <input

        type="password"

        placeholder="Current Password"

        value={currentPassword}

        onChange={
          (e)=>setCurrentPassword(e.target.value)
        }

        style={{
          width:"100%",
          padding:"10px",
          marginBottom:"10px"
        }}

      />



      <input

        type="password"

        placeholder="New Password"

        value={newPassword}

        onChange={
          (e)=>setNewPassword(e.target.value)
        }

        style={{
          width:"100%",
          padding:"10px",
          marginBottom:"10px"
        }}

      />



      <input

        type="password"

        placeholder="Confirm Password"

        value={confirmPassword}

        onChange={
          (e)=>setConfirmPassword(e.target.value)
        }

        style={{
          width:"100%",
          padding:"10px",
          marginBottom:"10px"
        }}

      />





      <button

        onClick={updatePassword}

        style={{
          padding:"10px 20px",
          cursor:"pointer"
        }}

      >

        Update Password


      </button>





      {
        passwordMessage && (

          <p style={{
            color:"green",
            fontWeight:"bold"
          }}>

            {passwordMessage}

          </p>

        )
      }






      <hr />



      <p>
        <strong>Role:</strong> {profile.role}
      </p>


      <p>
        <strong>Created At:</strong> {profile.created_at}
      </p>



    </div>

  );

}


export default ProfilePage;